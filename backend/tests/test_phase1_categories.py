from pathlib import Path

from backend.core.pipeline import PodcastPipeline


def _headline_tags(category: str, count: int) -> str:
    return "".join(f"<HEADLINE>{category} headline {i}</HEADLINE>" for i in range(count))


def test_categories_none_cycles_defaults(state, openai_api_key, perplexity_api_key, monkeypatch):
    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy_mistral",
        state=state,
    )

    calls = []

    def _fake_get_top_headlines(category: str, count: int = 1):
        calls.append((category, count))
        return {"content": _headline_tags(category, count), "citations": []}

    monkeypatch.setattr(pipeline.scraper, "get_top_headlines", _fake_get_top_headlines)

    articles = pipeline._get_articles_from_perplexity(num_articles=3, categories=None)
    assert [a.title for a in articles] == [
        "Technology headline 0",
        "Science headline 0",
        "Business headline 0",
    ]
    assert calls == [
        ("Technology", 1),
        ("Science", 1),
        ("Business", 1),
    ]


def test_categories_list_with_none_uses_random_choice(state, openai_api_key, perplexity_api_key, monkeypatch):
    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy_mistral",
        state=state,
    )

    # Force deterministic "random" category selection
    import backend.core.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod.random, "choice", lambda seq: "Science")

    calls = []

    def _fake_get_top_headlines(category: str, count: int = 1):
        calls.append((category, count))
        return {"content": _headline_tags(category, count), "citations": []}

    monkeypatch.setattr(pipeline.scraper, "get_top_headlines", _fake_get_top_headlines)

    articles = pipeline._get_articles_from_perplexity(num_articles=1, categories=[None])
    assert articles[0].title == "Science headline 0"
    assert calls == [("Science", 1)]


def test_duplicate_category_reuses_second_headline_without_extra_calls(
    state, openai_api_key, perplexity_api_key, monkeypatch
):
    pipeline = PodcastPipeline(
        perplexity_api_key=perplexity_api_key,
        openai_api_key=openai_api_key,
        mistral_api_key="dummy_mistral",
        state=state,
    )

    calls = []

    def _fake_get_top_headlines(category: str, count: int = 1):
        calls.append((category, count))
        return {"content": _headline_tags(category, count), "citations": []}

    monkeypatch.setattr(pipeline.scraper, "get_top_headlines", _fake_get_top_headlines)

    articles = pipeline._get_articles_from_perplexity(
        num_articles=2,
        categories=["Technology", "Technology"],
    )

    assert [a.title for a in articles] == ["Technology headline 0", "Technology headline 1"]
    assert calls == [("Technology", 2)]

