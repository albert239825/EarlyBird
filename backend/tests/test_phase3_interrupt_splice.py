import os

import pytest


@pytest.mark.skip(reason="Phase 3 stub: implement interrupt splice without Perplexity search")
def test_phase3_interrupt_inserts_dynamic_segments_unit():
    """
    Unit test stub (mocked):
    - Given an existing manifest and a segment_index:
      - /interrupt should insert dynamic segments at resume_segment_index = segment_index + 1
      - return updated manifest + inserted_segment_ids + resume_segment_index
    """
    raise NotImplementedError


@pytest.mark.integration
@pytest.mark.skip(reason="Phase 3 stub: run after implementing Phase 3 end-to-end interrupt splice")
def test_phase3_interrupt_splice_integration_smoke():
    """
    Integration stub (real APIs):
    - Requires: ELEVENLABS_API_KEY + MISTRAL_API_KEY (+ Whisper working)
    - Create a podcast with manifest + pregen audio.
    - Call /interrupt with a short recorded question and print the inserted segments.
    """
    if not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("ELEVENLABS_API_KEY not set")
    if not os.getenv("MISTRAL_API_KEY"):
        pytest.skip("MISTRAL_API_KEY not set")
    raise NotImplementedError

