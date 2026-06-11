import os

import pytest

from backend.agents.openai_script_writer import OpenAIScriptWriter


class _DummyResp:
    def __init__(self, content: str):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


def test_openai_script_writer_parses_json(monkeypatch):
    writer = OpenAIScriptWriter(api_key="dummy", model="dummy")

    def _fake_create(*args, **kwargs):
        return _DummyResp(
            '{"utterances":[{"utterance_id":"u0","speaker":"host","text":"Hello."},{"utterance_id":"u1","speaker":"expert","text":"Hi."}]}'
        )

    monkeypatch.setattr(writer.client.chat.completions, "create", _fake_create)

    utterances = writer.write_episode_script(
        stories=[{"headline": "Test", "research_md": "Research"}],
        max_utterances_total=4,
    )
    assert len(utterances) == 2
    assert utterances[0]["speaker"] == "host"
    assert utterances[1]["speaker"] == "expert"
    assert utterances[0]["text"]


def test_openai_script_writer_filters_invalid_utterances(monkeypatch):
    writer = OpenAIScriptWriter(api_key="dummy", model="dummy")

    def _fake_create(*args, **kwargs):
        return _DummyResp(
            '{"utterances":[{"utterance_id":"u0","speaker":"narrator","text":"Nope"},{"utterance_id":"u1","speaker":"host","text":"Ok"}]}'
        )

    monkeypatch.setattr(writer.client.chat.completions, "create", _fake_create)

    utterances = writer.write_episode_script(
        stories=[{"headline": "Test", "research_md": "Research"}],
        max_utterances_total=4,
    )
    assert utterances == [{"utterance_id": "u1", "speaker": "host", "text": "Ok"}]


@pytest.mark.integration
def test_openai_script_writer_integration_smoke():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    writer = OpenAIScriptWriter(api_key=os.environ["OPENAI_API_KEY"])
    utterances = writer.write_episode_script(
        stories=[{
            "headline": "A quick update on renewable energy adoption.",
            "research_md": "## Core_summary\nAdoption is rising due to policy and cost declines.\n",
        }],
        max_utterances_total=4,
    )
    assert utterances
    assert utterances[0]["speaker"] in ("host", "expert")

    # Print output for inspection
    print(f"\n{'='*60}")
    print(f"Integration test: Generated {len(utterances)} utterances")
    print(f"{'='*60}")
    for i, u in enumerate(utterances[:5]):  # Show first 5
        print(f"{i+1}. [{u['speaker'].upper()}]: {u['text'][:100]}...")
    if len(utterances) > 5:
        print(f"... and {len(utterances) - 5} more utterances")
    print(f"{'='*60}\n")
