import json
from pathlib import Path

from backend.core.pipeline import PodcastPipeline


class _FakeAudioGen:
    def __init__(self):
        self.calls = []

    def generate_segment(self, speaker: str, text: str, output_path: str):
        self.calls.append((speaker, text, output_path))
        return 1000


def test_phase2_orders_intro_then_stories_then_outro(tmp_podcast_dir: Path, state, openai_api_key, perplexity_api_key):
    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy_mistral",
        state=state,
    )

    script_dir = tmp_podcast_dir / "script"
    script_dir.mkdir(parents=True, exist_ok=True)

    (script_dir / "intro.json").write_text(
        json.dumps(
            {
                "story_index": -1,
                "utterances": [
                    {"utterance_id": "u0", "speaker": "host", "text": "Intro line"}
                ],
            }
        ),
        encoding="utf-8",
    )
    (script_dir / "story_0.json").write_text(
        json.dumps(
            {
                "story_index": 0,
                "utterances": [
                    {"utterance_id": "u0", "speaker": "host", "text": "Story0 line"}
                ],
            }
        ),
        encoding="utf-8",
    )
    (script_dir / "outro.json").write_text(
        json.dumps(
            {
                "story_index": -2,
                "utterances": [
                    {"utterance_id": "u0", "speaker": "host", "text": "Outro line"}
                ],
            }
        ),
        encoding="utf-8",
    )

    fake_audio = _FakeAudioGen()
    manifest = pipeline.generate_audio_segments_and_manifest(tmp_podcast_dir, fake_audio)

    # Ensure generation happened in intro -> story -> outro order
    assert [t for (_, t, _) in fake_audio.calls] == ["Intro line", "Story0 line", "Outro line"]
    assert [seg["text"] for seg in manifest["segments"]] == ["Intro line", "Story0 line", "Outro line"]

