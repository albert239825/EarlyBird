import os

import pytest


@pytest.mark.skip(reason="Phase 4 stub: implement NEED_SEARCH -> Perplexity -> rewrite -> research append")
def test_phase4_interrupt_appends_research_unit():
    """
    Unit test stub (mocked):
    - If expert responder returns NEED_SEARCH:
      - call Perplexity
      - append a new entry under ## Q_and_A_additions in research/story_k.md
      - insert dynamic answer segment into manifest
    """
    raise NotImplementedError


@pytest.mark.integration
@pytest.mark.skip(reason="Phase 4 stub: run after implementing Phase 4 end-to-end search + append")
def test_phase4_interrupt_search_append_integration_smoke():
    """
    Integration stub (real APIs):
    - Requires: PERPLEXITY_API_KEY + MISTRAL_API_KEY + ELEVENLABS_API_KEY
    - Ask an out-of-research question; confirm search triggered and research doc grew.
    """
    if not os.getenv("PERPLEXITY_API_KEY"):
        pytest.skip("PERPLEXITY_API_KEY not set")
    if not os.getenv("MISTRAL_API_KEY"):
        pytest.skip("MISTRAL_API_KEY not set")
    if not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("ELEVENLABS_API_KEY not set")
    raise NotImplementedError

