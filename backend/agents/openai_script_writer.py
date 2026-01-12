import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI


class OpenAIScriptWriter:
    """
    High-quality script writer that produces a full, structured script in one call.

    Output contract (Python): list of utterances:
      [{"utterance_id": "u0", "speaker": "host"|"expert", "text": "..."}]
    """

    def __init__(self, api_key: str, model: Optional[str] = None):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIScriptWriter")
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_SCRIPT_MODEL", "gpt-4o")

    def write_story_script(self, headline: str, research_md: str, max_utterances: int = 14) -> List[Dict[str, str]]:
        """
        Generate a host/expert conversation script for a single story.
        """
        system = (
            "You write concise, high-quality news podcast scripts similar to NPR up first.\n"
            "Return ONLY valid JSON.\n"
            "No markdown, no extra keys.\n"
            "Keep each utterance 4-6 sentences.\n"
            "Keep each story 3-4 minutes long.\n"
        )
        user = f"""
Write a short back-and-forth between a host and an expert about this story.

Requirements:
- Output JSON with EXACTLY this shape:
  {{
    "utterances": [
      {{"utterance_id": "u0", "speaker": "host", "text": "..."}},
      {{"utterance_id": "u1", "speaker": "expert", "text": "..."}}
    ]
  }}
- speaker must be "host" or "expert" (lowercase).
- utterance_id must be sequential: u0, u1, ...
- Maximum utterances: {max_utterances}
- Start with the host. End with the host wrapping up the story.

Headline:
{headline}

Research document:
{research_md}
""".strip()

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.6,
        )

        content = resp.choices[0].message.content or ""
        data = json.loads(content)
        utterances = data.get("utterances")
        if not isinstance(utterances, list) or not utterances:
            raise ValueError("OpenAI script writer returned no utterances")

        cleaned: List[Dict[str, str]] = []
        for i, u in enumerate(utterances):
            if not isinstance(u, dict):
                continue
            speaker = u.get("speaker")
            text = u.get("text")
            utterance_id = u.get("utterance_id", f"u{i}")
            if speaker not in ("host", "expert"):
                continue
            if not isinstance(text, str) or not text.strip():
                continue
            cleaned.append(
                {
                    "utterance_id": str(utterance_id),
                    "speaker": speaker,
                    "text": text.strip(),
                }
            )

        if not cleaned:
            raise ValueError("OpenAI script writer returned invalid utterances")
        return cleaned

