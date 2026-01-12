import json
from pathlib import Path

from backend.core.pipeline import PodcastPipeline


def test_split_episode_utterances_writes_intro_outro_and_prepends_transitions(
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

    # Stub headlines fetch
    def _fake_get_top_headlines(category: str, count: int = 1):
        content = "".join(f"<HEADLINE>Headline {i}</HEADLINE>" for i in range(count))
        return {"content": content, "citations": []}

    monkeypatch.setattr(pipeline.scraper, "get_top_headlines", _fake_get_top_headlines)

    # Stub research
    def _fake_research_stories(headline, abstract):
        return [
            {
                "headline": headline,
                "research": {
                    "choices": [{"message": {"content": "Research content"}}],
                    "citations": [],
                },
            }
        ]

    monkeypatch.setattr(pipeline.researcher, "research_stories", _fake_research_stories)

    # Episode writer returns tagged utterances
    def _fake_write_episode_script(stories, max_utterances_total: int = 48):
        return [
            {"utterance_id": "u0", "speaker": "host", "text": "<INTRO>Welcome—coming up..."},
            {"utterance_id": "u1", "speaker": "host", "text": "<STORY_0>Story zero starts."},
            {"utterance_id": "u2", "speaker": "expert", "text": "<STORY_0>Expert on story zero."},
            {"utterance_id": "u3", "speaker": "host", "text": "<TRANSITION_0_1>Now, onto story one."},
            {"utterance_id": "u4", "speaker": "host", "text": "<STORY_1>Story one starts."},
            {"utterance_id": "u5", "speaker": "host", "text": "<OUTRO>That’s it—see you tomorrow."},
        ]

    monkeypatch.setattr(pipeline.openai_script_writer, "write_episode_script", _fake_write_episode_script)

    pipeline.generate_research_and_script_assets(tmp_podcast_dir, num_articles=2)

    script_dir = tmp_podcast_dir / "script"
    intro = json.loads((script_dir / "intro.json").read_text(encoding="utf-8"))
    outro = json.loads((script_dir / "outro.json").read_text(encoding="utf-8"))
    story0 = json.loads((script_dir / "story_0.json").read_text(encoding="utf-8"))
    story1 = json.loads((script_dir / "story_1.json").read_text(encoding="utf-8"))

    assert intro["story_index"] == -1
    assert intro["utterances"][0]["text"].startswith("Welcome")
    assert "<INTRO>" not in intro["utterances"][0]["text"]

    assert outro["story_index"] == -2
    assert "see you tomorrow" in outro["utterances"][0]["text"].lower()
    assert "<OUTRO>" not in outro["utterances"][0]["text"]

    # Transition 0_1 should be prepended to story 1
    assert story0["story_index"] == 0
    assert [u["text"] for u in story0["utterances"]] == [
        "Story zero starts.",
        "Expert on story zero.",
    ]
    assert story1["story_index"] == 1
    assert [u["text"] for u in story1["utterances"]][:2] == [
        "Now, onto story one.",
        "Story one starts.",
    ]
    assert "<TRANSITION_0_1>" not in story1["utterances"][0]["text"]

