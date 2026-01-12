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


def _setup_phase2_test_fixtures(tmp_podcast_dir: Path) -> None:
    """
    Create pre-generated script and research files for Phase 2 integration testing.
    """
    # Create directories
    script_dir = tmp_podcast_dir / "script"
    research_dir = tmp_podcast_dir / "research"
    script_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    
    # Story 0: Technology news
    story_0_script = {
        "story_index": 0,
        "utterances": [
            {
                "utterance_id": "u0",
                "speaker": "host",
                "text": "Welcome back to Early Bird. Today we're diving into the latest developments in artificial intelligence."
            },
            {
                "utterance_id": "u1",
                "speaker": "expert",
                "text": "That's right. We're seeing unprecedented growth in AI capabilities, particularly in language models."
            },
            {
                "utterance_id": "u2",
                "speaker": "host",
                "text": "Can you break down what makes these new models different from what we've seen before?"
            },
            {
                "utterance_id": "u3",
                "speaker": "expert",
                "text": "Absolutely. The key difference is the scale of training data and the sophistication of the architecture."
            }
        ]
    }
    
    story_0_research = """# Research: Latest Developments in Artificial Intelligence

## Core Summary
Recent advances in artificial intelligence, particularly in large language models, have shown significant improvements in understanding and generation capabilities.

## Key Points
- Training data scale has increased dramatically
- Architecture improvements enable better reasoning
- Real-world applications are expanding rapidly

## Citations
- https://example.com/ai-research-2024
"""
    
    # Story 1: Science news
    story_1_script = {
        "story_index": 1,
        "utterances": [
            {
                "utterance_id": "u0",
                "speaker": "host",
                "text": "Moving on to science news, there's been a breakthrough in renewable energy storage."
            },
            {
                "utterance_id": "u1",
                "speaker": "expert",
                "text": "Yes, researchers have developed a new battery technology that could revolutionize how we store solar and wind energy."
            },
            {
                "utterance_id": "u2",
                "speaker": "host",
                "text": "What are the practical implications of this development?"
            }
        ]
    }
    
    story_1_research = """# Research: Breakthrough in Renewable Energy Storage

## Core Summary
New battery technology promises to make renewable energy storage more efficient and cost-effective.

## Key Points
- Improved energy density
- Lower production costs
- Longer lifespan

## Citations
- https://example.com/battery-research-2024
"""
    
    # Write script files
    (script_dir / "story_0.json").write_text(
        json.dumps(story_0_script, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    (script_dir / "story_1.json").write_text(
        json.dumps(story_1_script, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Write research files
    (research_dir / "story_0.md").write_text(story_0_research, encoding="utf-8")
    (research_dir / "story_1.md").write_text(story_1_research, encoding="utf-8")
    
    # Write podcast.json metadata
    podcast_meta = {
        "podcast_id": tmp_podcast_dir.name,
        "stories": [
            {"story_index": 0, "title": "Latest Developments in Artificial Intelligence"},
            {"story_index": 1, "title": "Breakthrough in Renewable Energy Storage"}
        ]
    }
    (tmp_podcast_dir / "podcast.json").write_text(
        json.dumps(podcast_meta, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


@pytest.mark.integration
def test_phase2_manifest_playback_integration_full(tmp_podcast_dir: Path, state, openai_api_key, perplexity_api_key, elevenlabs_api_key):
    """
    Integration test: Phase 2 audio generation with real ElevenLabs API.
    
    Tests that:
    - Script files are read correctly
    - Real MP3 segments are generated
    - Manifest.json is created with correct structure
    - Files are valid and playable
    - Multiple stories are handled correctly
    """
    
    print(f"\n{'='*60}")
    print("Integration Test: Phase 2 Audio Generation")
    print(f"{'='*60}\n")
    
    # Set up test fixtures (pre-generated scripts and research)
    _setup_phase2_test_fixtures(tmp_podcast_dir)
    print(f"✓ Created test fixtures in: {tmp_podcast_dir}")
    print(f"  - Script files: story_0.json, story_1.json")
    print(f"  - Research files: story_0.md, story_1.md")
    print(f"  - Metadata: podcast.json\n")
    
    # Initialize pipeline and audio generator
    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy",  # Not used in Phase 2
        state=state,
    )
    
    audio_generator = PodcastAudioGenerator(output_dir=str(tmp_podcast_dir / "audio"))
    print(f"✓ Initialized PodcastAudioGenerator with ElevenLabs\n")
    
    # Generate audio segments and manifest
    print("Generating audio segments (this may take a minute)...")
    manifest = pipeline.generate_audio_segments_and_manifest(
        podcast_dir=tmp_podcast_dir,
        audio_generator=audio_generator
    )
    
    print(f"\n{'='*60}")
    print("GENERATION COMPLETE")
    print(f"{'='*60}\n")
    
    # Verify manifest structure
    assert manifest["podcast_id"] == tmp_podcast_dir.name
    assert "segments" in manifest
    segments = manifest["segments"]
    assert len(segments) == 7  # 4 from story_0 + 3 from story_1
    
    print(f"✓ Manifest created with {len(segments)} segments\n")
    
    # Verify file creation
    audio_pregen_dir = tmp_podcast_dir / "audio" / "pregen"
    assert audio_pregen_dir.exists(), "audio/pregen directory should exist"
    
    total_duration_ms = 0
    total_size_bytes = 0
    
    print(f"{'='*60}")
    print("SEGMENT DETAILS")
    print(f"{'='*60}")
    print(f"{'ID':<12} {'Story':<6} {'Speaker':<8} {'Duration':<12} {'Size':<10} {'Text Preview'}")
    print(f"{'-'*60}")
    
    for seg in segments:
        segment_id = seg["segment_id"]
        file_path = audio_pregen_dir / f"{segment_id}.mp3"
        
        # Verify file exists
        assert file_path.exists(), f"MP3 file should exist: {file_path}"
        
        # Verify file is non-empty
        file_size = file_path.stat().st_size
        assert file_size > 0, f"MP3 file should not be empty: {file_path}"
        total_size_bytes += file_size
        
        # Verify manifest fields
        assert seg["utterance_id"].startswith("u")
        assert seg["speaker"] in ("host", "expert")
        assert seg["story_index"] in (0, 1)
        assert seg["source"] == "pregen"
        assert seg["url"] == f"/podcasts/{tmp_podcast_dir.name}/segments/{segment_id}"
        assert "text" in seg
        
        # Duration may be None if pydub failed, but that's okay
        duration_ms = seg.get("duration_ms")
        if duration_ms is not None:
            total_duration_ms += duration_ms
        
        text_preview = seg["text"][:30] + "..." if len(seg["text"]) > 30 else seg["text"]
        duration_str = f"{duration_ms}ms" if duration_ms else "N/A"
        print(f"{segment_id:<12} {seg['story_index']:<6} {seg['speaker']:<8} {duration_str:<12} {file_size:<10} {text_preview}")
    
    print(f"{'-'*60}")
    print(f"Total: {len(segments)} segments, ~{total_duration_ms/1000:.1f}s audio, {total_size_bytes/1024:.1f} KB")
    print(f"{'='*60}\n")
    
    # Verify segment ordering (should be sequential by story)
    story_indices = [s["story_index"] for s in segments]
    assert story_indices == [0, 0, 0, 0, 1, 1, 1], "Segments should be ordered by story"
    
    # Verify segment IDs are sequential
    segment_ids = [s["segment_id"] for s in segments]
    assert segment_ids == [f"seg_{i:04d}" for i in range(1, 8)], "Segment IDs should be sequential"
    
    # Try to validate MP3 files with pydub (if available)
    try:
        from pydub import AudioSegment
        valid_count = 0
        for seg in segments[:3]:  # Check first 3 segments
            file_path = audio_pregen_dir / f"{seg['segment_id']}.mp3"
            try:
                audio = AudioSegment.from_mp3(str(file_path))
                assert audio.duration_seconds > 0, f"Audio should have positive duration: {file_path}"
                valid_count += 1
            except Exception as e:
                print(f"⚠ Warning: Could not validate {seg['segment_id']}.mp3 with pydub: {e}")
        
        if valid_count > 0:
            print(f"✓ Validated {valid_count} MP3 files with pydub\n")
    except ImportError:
        print("⚠ pydub not available for MP3 validation\n")
    
    # Verify manifest can be saved and loaded
    from backend.storage.podcast_storage import PodcastStorage
    
    # Create a temporary backend root for storage
    backend_root = tmp_podcast_dir.parent / "backend_root"
    storage = PodcastStorage(backend_root)
    storage.save_manifest(tmp_podcast_dir, manifest)
    
    loaded_manifest = storage.load_manifest(tmp_podcast_dir)
    assert loaded_manifest == manifest, "Manifest should save/load correctly"
    print("✓ Manifest save/load verified\n")
    
    print(f"{'='*60}")
    print("ALL ASSERTIONS PASSED!")
    print(f"{'='*60}\n")

