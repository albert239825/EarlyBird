import os

import pytest


@pytest.mark.skip(reason="Phase 2 stub: implement manifest + segment endpoints and pregen audio")
def test_phase2_manifest_schema_unit():
    """
    Unit test stub (mocked):
    - After Phase 2, generation should produce manifest.json with:
      - podcast_id
      - segments[] with {segment_id, story_index, utterance_id, speaker, text, url, duration_ms, source}
    """
    raise NotImplementedError


@pytest.mark.integration
@pytest.mark.skip(reason="Phase 2 stub: run after implementing Phase 2 end-to-end generation")
def test_phase2_manifest_playback_integration_smoke():
    """
    Integration stub (real APIs):
    - Run /generate (or directly call service) to create a podcast with pregen audio.
    - Fetch /podcasts/<podcast_id>/manifest and print first 3 segments.
    - Fetch one /segments/<segment_id> and confirm it returns MP3 bytes.
    """
    if not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("ELEVENLABS_API_KEY not set")
    raise NotImplementedError

