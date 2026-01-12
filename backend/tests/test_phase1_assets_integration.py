import json
import os
from pathlib import Path

import pytest

from backend.core.pipeline import PodcastPipeline


@pytest.mark.integration
def test_generate_research_and_script_assets_integration_full_pipeline(
    tmp_podcast_dir: Path, state
):
    """
    Integration test: full Phase 1 pipeline with real Perplexity + OpenAI calls.
    """
    if not os.getenv("PERPLEXITY_API_KEY"):
        pytest.skip("PERPLEXITY_API_KEY not set")
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    pipeline = PodcastPipeline(
        perplexity_api_key=os.environ["PERPLEXITY_API_KEY"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        mistral_api_key="dummy_mistral",  # Not used in Phase 1
        state=state,
    )

    print(f"\n{'='*60}")
    print("Integration Test: Full Phase 1 Pipeline")
    print(f"{'='*60}\n")

    # Generate assets (real API calls)
    out = pipeline.generate_research_and_script_assets(tmp_podcast_dir, num_articles=1)

    print(f"✓ Generated podcast_id: {out['podcast_id']}")
    print(f"✓ Stories: {len(out.get('stories', []))}\n")

    # Verify files exist
    assert (tmp_podcast_dir / "podcast.json").exists()
    assert (tmp_podcast_dir / "research" / "story_0.md").exists()
    assert (tmp_podcast_dir / "script" / "story_0.json").exists()

    # Read and display headline
    podcast_meta = json.loads(
        (tmp_podcast_dir / "podcast.json").read_text(encoding="utf-8")
    )
    headline = podcast_meta["stories"][0]["title"]
    print(f"{'='*60}")
    print("HEADLINE (from Perplexity):")
    print(f"  {headline}")
    print(f"{'='*60}\n")

    # Read and display research doc
    research_md = (tmp_podcast_dir / "research" / "story_0.md").read_text(
        encoding="utf-8"
    )
    print(f"{'='*60}")
    print("RESEARCH DOCUMENT (from Perplexity):")
    print(f"{'='*60}")
    preview = research_md[:500] + ("..." if len(research_md) > 500 else "")
    print(preview)
    print(f"{'='*60}\n")

    # Read and display script utterances
    script = json.loads(
        (tmp_podcast_dir / "script" / "story_0.json").read_text(encoding="utf-8")
    )
    utterances = script["utterances"]
    print(f"{'='*60}")
    print(f"GENERATED SCRIPT (from OpenAI): {len(utterances)} utterances")
    print(f"{'='*60}")
    for i, u in enumerate(utterances[:8]):
        text_preview = u["text"][:120] + ("..." if len(u["text"]) > 120 else "")
        print(f"{i+1}. [{u['speaker'].upper():6s}]: {text_preview}")
    if len(utterances) > 8:
        print(f"... and {len(utterances) - 8} more utterances")
    print(f"{'='*60}\n")

    # Assertions
    assert out["podcast_id"] == tmp_podcast_dir.name
    assert len(out["stories"]) == 1
    assert headline
    assert research_md
    assert len(utterances) > 0
    assert all(u["speaker"] in ("host", "expert") for u in utterances)

    # State updated
    assert len(state.articles) == 1
    assert state.articles[0]["article_data"].title == headline
    assert "research" in state.articles[0]
    assert "script" in state.articles[0]

    print("✓ All assertions passed!\n")

