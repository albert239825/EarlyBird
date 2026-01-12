import json
import os
from typing import Any, Dict, List, Optional
import dotenv
from openai import OpenAI
import logging
from backend.config import Config

dotenv.load_dotenv()

logger = logging.getLogger(__name__)


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
        self.model = model or Config.OPENAI_SCRIPT_MODEL

#     def write_story_script(self, headline: str, research_md: str, max_utterances: int = 14) -> List[Dict[str, str]]:
#         """
#         Generate a host/expert conversation script for a single story.
#         """
#         system = (
#             "You write concise, high-quality news podcast scripts similar to NPR up first.\n"
#             "Return ONLY valid JSON.\n"
#             "No markdown, no extra keys.\n"
#             "Keep each utterance 4-6 sentences.\n"
#             "Keep each story 3-4 minutes long.\n"
#         )
#         user = f"""
# Write a short back-and-forth between a host and an expert about this story.

# Requirements:
# - Output JSON with EXACTLY this shape:
#   {{
#     "utterances": [
#       {{"utterance_id": "u0", "speaker": "host", "text": "..."}},
#       {{"utterance_id": "u1", "speaker": "expert", "text": "..."}}
#     ]
#   }}
# - speaker must be "host" or "expert" (lowercase).
# - utterance_id must be sequential: u0, u1, ...
# - Maximum utterances: {max_utterances}
# - Start with the host. End with the host wrapping up the story.

# Headline:
# {headline}

# Research document:
# {research_md}
# """.strip()

#         resp = self.client.chat.completions.create(
#             model=self.model,
#             messages=[
#                 {"role": "system", "content": system},
#                 {"role": "user", "content": user},
#             ],
#             response_format={"type": "json_object"},
#             temperature=0.6,
#         )

#         content = resp.choices[0].message.content or ""
#         data = json.loads(content)
#         utterances = data.get("utterances")
#         if not isinstance(utterances, list) or not utterances:
#             raise ValueError("OpenAI script writer returned no utterances")

#         cleaned: List[Dict[str, str]] = []
#         for i, u in enumerate(utterances):
#             if not isinstance(u, dict):
#                 continue
#             speaker = u.get("speaker")
#             text = u.get("text")
#             utterance_id = u.get("utterance_id", f"u{i}")
#             if speaker not in ("host", "expert"):
#                 continue
#             if not isinstance(text, str) or not text.strip():
#                 continue
#             cleaned.append(
#                 {
#                     "utterance_id": str(utterance_id),
#                     "speaker": speaker,
#                     "text": text.strip(),
#                 }
#             )

#         if not cleaned:
#             raise ValueError("OpenAI script writer returned invalid utterances")
#         return cleaned

    def write_episode_script(
        self,
        stories: List[Dict[str, str]],
        max_utterances_total: int = 48,
    ) -> List[Dict[str, str]]:
        """
        Generate a full episode script (intro + stories + transitions + outro) in one call.

        Each utterance text MUST begin with exactly one tag:
          <INTRO>
          <STORY_0>, <STORY_1>, ...
          <TRANSITION_0_1>, <TRANSITION_1_2>, ...
          <OUTRO>
        """
        system = (
            "You write concise, high-quality news podcast scripts similar to NPR up first.\n"
            "Return ONLY valid JSON.\n"
            "No markdown, no extra keys.\n"
            "Keep each utterance 2-5 sentences.\n"
        )

        # Provide a compact, structured episode input so the model can create coherent transitions.
        # Truncate research docs to avoid token limit issues (keep first ~2000 chars per story)
        MAX_RESEARCH_CHARS_PER_STORY = 2000
        stories_blob = []
        for i, s in enumerate(stories):
            headline = s.get("headline", "").strip()
            research_md = s.get("research_md", "").strip()
            # Truncate if too long, preserving markdown structure
            if len(research_md) > MAX_RESEARCH_CHARS_PER_STORY:
                research_md = research_md[:MAX_RESEARCH_CHARS_PER_STORY] + "\n\n[... research truncated for length ...]"
            category = (s.get("category") or "").strip()
            stories_blob.append(
                "\n".join(
                    [
                        f"STORY_INDEX: {i}",
                        f"CATEGORY: {category}" if category else "CATEGORY: (unspecified)",
                        "HEADLINE:",
                        headline,
                        "",
                        "RESEARCH_DOCUMENT:",
                        research_md,
                        "",
                    ]
                )
            )

        user = f"""
Write a single episode script with a host and an expert.

Hard requirements:
- Output JSON with EXACTLY this shape:
  {{
    "utterances": [
      {{"utterance_id": "u0", "speaker": "host", "text": "<INTRO>..."}},
      {{"utterance_id": "u1", "speaker": "expert", "text": "<INTRO>..."}}
    ]
  }}
- speaker must be "host" or "expert" (lowercase).
- utterance_id must be sequential: u0, u1, ...
- Maximum utterances: {max_utterances_total}
- EVERY utterance text MUST start with exactly ONE of these tags (no exceptions):
  - <INTRO>
  - <STORY_0>, <STORY_1>, ... (use the correct story index)
  - <TRANSITION_0_1>, <TRANSITION_1_2>, ... (transition from story A to story B)
  - <OUTRO>
- Intro: 2-4 short phrases previewing the stories ahead ("coming up..."), friendly but concise.
- Between stories: include a host-led transition that references a takeaway from the previous story and tees up the next.
- Outro: host must say the exact phrase "see you tomorrow".

Episode stories (in order):
{os.linesep.join(stories_blob)}
""".strip()

        # Log request info for debugging
        total_chars = len(user)
        logger.info(f"Calling OpenAI API with model={self.model}, prompt_length={total_chars} chars, num_stories={len(stories)}")
        
        try:
            resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.6,
            timeout=120.0,  # 2 minute timeout to prevent hanging
            )
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
        
        logger.info("OpenAI API call completed successfully")
        content = resp.choices[0].message.content or ""
        data = json.loads(content)
        utterances = data.get("utterances")
        if not isinstance(utterances, list) or not utterances:
            raise ValueError("OpenAI episode script writer returned no utterances")

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
            raise ValueError("OpenAI episode script writer returned invalid utterances")
        return cleaned

