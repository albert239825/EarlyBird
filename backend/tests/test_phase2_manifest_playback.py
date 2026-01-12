import json
import os
from pathlib import Path

import pytest
from flask import Flask

from backend.api.routes import setup_routes
from backend.audio.generator import PodcastAudioGenerator
from backend.core.pipeline import PodcastPipeline
from backend.storage.podcast_storage import PodcastStorage


def _make_dummy_elevenlabs(monkeypatch, *, write_bytes: bytes = b"fake_mp3_data"):
    """
    Patch backend.audio.generator.ElevenLabs to a dummy client that records calls.
    """
    import backend.audio.generator as gen_mod

    calls = []

    class _DummyTTS:
        @staticmethod
        def convert(**kwargs):
            calls.append(kwargs)
            # ElevenLabs SDK returns an iterator of bytes chunks.
            return iter([write_bytes])

    class _DummyClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.text_to_speech = _DummyTTS()

    monkeypatch.setattr(gen_mod, "ElevenLabs", _DummyClient)
    return calls


def test_audio_generator_generate_segment_creates_mp3(tmp_path: Path, monkeypatch):
    # Ensure init passes
    monkeypatch.setenv("ELEVENLABS_API_KEY", "dummy")

    calls = _make_dummy_elevenlabs(monkeypatch)

    # Mock pydub duration
    import backend.audio.generator as gen_mod

    class _DummyAudio:
        duration_seconds = 4.2

    monkeypatch.setattr(gen_mod.AudioSegment, "from_mp3", lambda *_args, **_kwargs: _DummyAudio())

    out_path = tmp_path / "out" / "seg_0001.mp3"
    gen = PodcastAudioGenerator(output_dir=str(tmp_path))
    duration_ms = gen.generate_segment("host", "Hello world", str(out_path))

    assert out_path.exists()
    assert out_path.read_bytes() == b"fake_mp3_data"
    assert duration_ms == 4200
    assert calls, "Expected ElevenLabs convert to be called"


def test_audio_generator_generate_segment_voice_mapping(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "dummy")
    calls = _make_dummy_elevenlabs(monkeypatch)

    # Avoid pydub dependency on ffmpeg in unit tests
    import backend.audio.generator as gen_mod
    monkeypatch.setattr(gen_mod.AudioSegment, "from_mp3", lambda *_a, **_k: type("A", (), {"duration_seconds": 0.0})())

    gen = PodcastAudioGenerator(output_dir=str(tmp_path))

    gen.generate_segment("host", "h", str(tmp_path / "h.mp3"))
    gen.generate_segment("expert", "e", str(tmp_path / "e.mp3"))
    gen.generate_segment("unknown", "u", str(tmp_path / "u.mp3"))

    assert calls[0]["voice_id"] == gen.SPEAKER_VOICES["host"]
    assert calls[1]["voice_id"] == gen.SPEAKER_VOICES["expert"]
    assert calls[2]["voice_id"] == gen.SPEAKER_VOICES["host"]


def test_audio_generator_generate_segment_returns_none_on_pydub_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "dummy")
    _make_dummy_elevenlabs(monkeypatch)

    import backend.audio.generator as gen_mod
    monkeypatch.setattr(gen_mod.AudioSegment, "from_mp3", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))

    gen = PodcastAudioGenerator(output_dir=str(tmp_path))
    duration_ms = gen.generate_segment("host", "Hello", str(tmp_path / "x.mp3"))
    assert duration_ms is None


def test_storage_save_and_load_manifest(tmp_podcast_dir: Path, tmp_backend_root: Path):
    storage = PodcastStorage(tmp_backend_root)
    manifest = {"podcast_id": tmp_podcast_dir.name, "segments": []}
    storage.save_manifest(tmp_podcast_dir, manifest)

    loaded = storage.load_manifest(tmp_podcast_dir)
    assert loaded == manifest


def test_storage_load_manifest_raises_when_missing(tmp_podcast_dir: Path, tmp_backend_root: Path):
    storage = PodcastStorage(tmp_backend_root)
    with pytest.raises(FileNotFoundError):
        storage.load_manifest(tmp_podcast_dir)


def test_storage_get_podcast_dir_resolves_path(tmp_backend_root: Path):
    storage = PodcastStorage(tmp_backend_root)
    assert storage.get_podcast_dir("podcast_123") == tmp_backend_root / "finished_podcasts" / "podcast_123"


def test_pipeline_generate_audio_segments_and_manifest_creates_segments(
    tmp_podcast_dir: Path,
    state,
    openai_api_key,
    perplexity_api_key,
    monkeypatch,
):
    # Prepare one script with 2 utterances
    script_dir = tmp_podcast_dir / "script"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "story_0.json").write_text(
        json.dumps(
            {
                "story_index": 0,
                "utterances": [
                    {"utterance_id": "u0", "speaker": "host", "text": "Host line."},
                    {"utterance_id": "u1", "speaker": "expert", "text": "Expert line."},
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy",
        state=state,
    )

    class _DummyAudioGen:
        def generate_segment(self, speaker: str, text: str, output_path: str):
            Path(output_path).write_bytes(b"fake_mp3_data")
            return 4200

    manifest = pipeline.generate_audio_segments_and_manifest(tmp_podcast_dir, _DummyAudioGen())

    assert manifest["podcast_id"] == tmp_podcast_dir.name
    assert len(manifest["segments"]) == 2

    seg0 = manifest["segments"][0]
    assert seg0["segment_id"] == "seg_0001"
    assert seg0["utterance_id"] == "u0"
    assert seg0["story_index"] == 0
    assert seg0["speaker"] == "host"
    assert seg0["source"] == "pregen"
    assert seg0["url"] == f"/podcasts/{tmp_podcast_dir.name}/segments/seg_0001"
    assert seg0["duration_ms"] == 4200

    assert (tmp_podcast_dir / "audio" / "pregen" / "seg_0001.mp3").exists()
    assert (tmp_podcast_dir / "audio" / "pregen" / "seg_0002.mp3").exists()


def test_pipeline_generate_audio_segments_and_manifest_multiple_stories(
    tmp_podcast_dir: Path,
    state,
    openai_api_key,
    perplexity_api_key,
    monkeypatch,
):
    script_dir = tmp_podcast_dir / "script"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "story_0.json").write_text(
        json.dumps(
            {
                "story_index": 0,
                "utterances": [
                    {"utterance_id": "u0", "speaker": "host", "text": "A"},
                    {"utterance_id": "u1", "speaker": "expert", "text": "B"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (script_dir / "story_1.json").write_text(
        json.dumps(
            {
                "story_index": 1,
                "utterances": [
                    {"utterance_id": "u0", "speaker": "host", "text": "C"},
                ],
            }
        ),
        encoding="utf-8",
    )

    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy",
        state=state,
    )

    class _DummyAudioGen:
        def generate_segment(self, speaker: str, text: str, output_path: str):
            Path(output_path).write_bytes(b"x")
            return 1

    manifest = pipeline.generate_audio_segments_and_manifest(tmp_podcast_dir, _DummyAudioGen())
    assert len(manifest["segments"]) == 3
    assert [s["story_index"] for s in manifest["segments"]] == [0, 0, 1]


def test_get_manifest_returns_200_with_manifest(tmp_backend_root: Path):
    podcast_id = "podcast_test_1"
    storage = PodcastStorage(tmp_backend_root)
    podcast_dir = storage.get_podcast_dir(podcast_id)
    podcast_dir.mkdir(parents=True, exist_ok=True)

    expected = {"podcast_id": podcast_id, "segments": []}
    storage.save_manifest(podcast_dir, expected)

    # Patch routes to use our temp backend root
    import backend.api.routes as routes_mod

    def _storage_factory(_backend_root):
        return PodcastStorage(tmp_backend_root)

    app = Flask(__name__)
    setup_routes(app, service=object())

    with app.test_request_context():
        pass

    client = app.test_client()
    # Monkeypatch after routes import but before call
    routes_mod.PodcastStorage = _storage_factory  # type: ignore

    resp = client.get(f"/podcasts/{podcast_id}/manifest")
    assert resp.status_code == 200
    assert resp.get_json() == expected


def test_get_manifest_returns_404_when_podcast_missing(tmp_backend_root: Path):
    import backend.api.routes as routes_mod

    routes_mod.PodcastStorage = lambda _backend_root: PodcastStorage(tmp_backend_root)  # type: ignore

    app = Flask(__name__)
    setup_routes(app, service=object())
    client = app.test_client()

    resp = client.get("/podcasts/does_not_exist/manifest")
    assert resp.status_code == 404


def test_get_segment_returns_200_with_mp3_bytes(tmp_backend_root: Path):
    podcast_id = "podcast_test_2"
    storage = PodcastStorage(tmp_backend_root)
    podcast_dir = storage.get_podcast_dir(podcast_id)
    (podcast_dir / "audio" / "pregen").mkdir(parents=True, exist_ok=True)
    (podcast_dir / "audio" / "pregen" / "seg_0001.mp3").write_bytes(b"mp3bytes")

    manifest = {
        "podcast_id": podcast_id,
        "segments": [
            {"segment_id": "seg_0001", "source": "pregen"},
        ],
    }
    storage.save_manifest(podcast_dir, manifest)

    import backend.api.routes as routes_mod
    routes_mod.PodcastStorage = lambda _backend_root: PodcastStorage(tmp_backend_root)  # type: ignore

    app = Flask(__name__)
    setup_routes(app, service=object())
    client = app.test_client()

    resp = client.get(f"/podcasts/{podcast_id}/segments/seg_0001")
    assert resp.status_code == 200
    assert resp.data == b"mp3bytes"
    assert resp.mimetype == "audio/mpeg"


def test_get_segment_returns_404_when_segment_not_in_manifest(tmp_backend_root: Path):
    podcast_id = "podcast_test_3"
    storage = PodcastStorage(tmp_backend_root)
    podcast_dir = storage.get_podcast_dir(podcast_id)
    podcast_dir.mkdir(parents=True, exist_ok=True)
    storage.save_manifest(podcast_dir, {"podcast_id": podcast_id, "segments": []})

    import backend.api.routes as routes_mod
    routes_mod.PodcastStorage = lambda _backend_root: PodcastStorage(tmp_backend_root)  # type: ignore

    app = Flask(__name__)
    setup_routes(app, service=object())
    client = app.test_client()

    resp = client.get(f"/podcasts/{podcast_id}/segments/seg_9999")
    assert resp.status_code == 404


def test_get_segment_returns_500_for_invalid_source(tmp_backend_root: Path):
    podcast_id = "podcast_test_4"
    storage = PodcastStorage(tmp_backend_root)
    podcast_dir = storage.get_podcast_dir(podcast_id)
    podcast_dir.mkdir(parents=True, exist_ok=True)
    storage.save_manifest(
        podcast_dir,
        {"podcast_id": podcast_id, "segments": [{"segment_id": "seg_0001", "source": "weird"}]},
    )

    import backend.api.routes as routes_mod
    routes_mod.PodcastStorage = lambda _backend_root: PodcastStorage(tmp_backend_root)  # type: ignore

    app = Flask(__name__)
    setup_routes(app, service=object())
    client = app.test_client()

    resp = client.get(f"/podcasts/{podcast_id}/segments/seg_0001")
    assert resp.status_code == 500


@pytest.mark.integration
@pytest.mark.skip(reason="Phase 2 integration: run when you want real MP3 generation")
def test_phase2_manifest_playback_integration_smoke():
    if not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("ELEVENLABS_API_KEY not set")
    raise NotImplementedError

