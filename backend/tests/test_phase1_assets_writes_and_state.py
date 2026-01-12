import json
from pathlib import Path

from backend.core.pipeline import PodcastPipeline


def test_generate_research_and_script_assets_writes_files(
    tmp_podcast_dir: Path,
    state,
    openai_api_key,
    perplexity_api_key,
    monkeypatch,
):
    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy_mistral",
        state=state,
    )

    def _fake_get_top_headlines(category: str, count: int = 1):
        content = "".join(
            f"<HEADLINE>Test Headline {i}</HEADLINE>" for i in range(count)
        )
        return {"content": content, "citations": []}

    monkeypatch.setattr(pipeline.scraper, "get_top_headlines", _fake_get_top_headlines)

    def _fake_research_stories(headline, abstract):
        return [
            {
                "headline": headline,
                "research": {
                    "choices": [{"message": {"content": "Research content"}}],
                    "citations": ["https://example.com/source"],
                },
            }
        ]

    monkeypatch.setattr(pipeline.researcher, "research_stories", _fake_research_stories)

    def _fake_write_story_script(headline, research_md, max_utterances=14):
        return [
            {"utterance_id": "u0", "speaker": "host", "text": "Host line."},
            {"utterance_id": "u1", "speaker": "expert", "text": "Expert line."},
        ]

    monkeypatch.setattr(
        pipeline.openai_script_writer, "write_story_script", _fake_write_story_script
    )

    out = pipeline.generate_research_and_script_assets(tmp_podcast_dir, num_articles=1)
    assert out["podcast_id"] == tmp_podcast_dir.name
    assert out["stories"][0]["title"] == "Test Headline 0"

    assert (tmp_podcast_dir / "podcast.json").exists()
    assert (tmp_podcast_dir / "research" / "story_0.md").exists()
    assert (tmp_podcast_dir / "script" / "story_0.json").exists()

    script = json.loads(
        (tmp_podcast_dir / "script" / "story_0.json").read_text(encoding="utf-8")
    )
    assert script["story_index"] == 0
    assert len(script["utterances"]) == 2

    assert len(state.articles) == 1
    assert state.articles[0]["article_data"].title == "Test Headline 0"
    assert "research" in state.articles[0]
    assert "script" in state.articles[0]
    assert state.articles[0]["script"]["texts"][0]["role"] == "host"

