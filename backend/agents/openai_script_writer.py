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
                research_md = (
                    research_md[:MAX_RESEARCH_CHARS_PER_STORY]
                    + "\n\n[... research truncated for length ...]"
                )
            category = (s.get("category") or "").strip()
            stories_blob.append(
                "\n".join(
                    [
                        f"STORY_INDEX: {i}",
                        (
                            f"CATEGORY: {category}"
                            if category
                            else "CATEGORY: (unspecified)"
                        ),
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

CRITICAL FORMATTING RULES:
- Create SEPARATE utterances for EACH section (intro, each story, each transition, outro)
- DO NOT combine multiple sections into one utterance
- DO NOT embed tags in the middle of text
- Each utterance text MUST START with exactly ONE tag, then the spoken content

Output JSON with EXACTLY this shape:
  {{
    "utterances": [
      {{"utterance_id": "u0", "speaker": "host", "text": "<INTRO>Welcome, coming up today..."}},
      {{"utterance_id": "u1", "speaker": "host", "text": "<STORY_0>Let's start with..."}},
      {{"utterance_id": "u2", "speaker": "expert", "text": "<STORY_0>That's right..."}},
      {{"utterance_id": "u3", "speaker": "host", "text": "<TRANSITION_0_1>Now moving on..."}},
      {{"utterance_id": "u4", "speaker": "host", "text": "<STORY_1>Next up..."}},
      {{"utterance_id": "u5", "speaker": "host", "text": "<OUTRO>That's it for today. See you tomorrow."}}
    ]
  }}

Requirements:
- speaker must be "host" or "expert" (lowercase).
- utterance_id must be sequential: u0, u1, ...
- Maximum utterances: {max_utterances_total}
- EVERY utterance text MUST start with exactly ONE of these tags (no exceptions):
  - <INTRO> (for intro section)
  - <STORY_0>, <STORY_1>, ... (for each story, use the correct index)
  - <TRANSITION_0_1>, <TRANSITION_1_2>, ... (for transitions between stories)
  - <OUTRO> (for closing)
- Intro: Create 1-2 utterances with <INTRO> tag previewing the stories ahead ("coming up..."), friendly but concise.
- Each story: Create MULTIPLE utterances (3-6 per story) with the <STORY_X> tag:
  * Host introduces the story
  * Expert provides analysis/context
  * Host asks follow-up or expert continues
  * Host wraps up that story
- Between stories: Create a SEPARATE utterance with <TRANSITION_X_Y> tag where host transitions from story X to story Y.
- Outro: Create 1 utterance with <OUTRO> tag where host says "see you tomorrow".

IMPORTANT: Each utterance must be a SEPARATE entry in the utterances array. Do NOT combine multiple sections into one utterance.

Episode stories (in order):
{os.linesep.join(stories_blob)}
""".strip()

        # Log request info for debugging
        total_chars = len(user)
        logger.info(
            f"Calling OpenAI API with model={self.model}, prompt_length={total_chars} chars, num_stories={len(stories)}"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                timeout=120.0,  # 2 minute timeout to prevent hanging
            )
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

        logger.info("OpenAI API call completed successfully")
        content = resp.choices[0].message.content or ""
        
        # Log raw response for debugging
        logger.info("=" * 80)
        logger.info("RAW OPENAI RESPONSE (first 2000 chars):")
        logger.info("=" * 80)
        logger.info(content[:2000] + ("..." if len(content) > 2000 else ""))
        logger.info("=" * 80)
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Full response content: {content}")
            raise
        
        utterances = data.get("utterances")
        
        # Log parsed utterances summary
        logger.info(f"Parsed {len(utterances) if utterances else 0} utterances from response")
        if utterances:
            for i, u in enumerate(utterances[:10]):  # Log first 10
                text_preview = u.get("text", "")[:100]
                speaker = u.get("speaker", "unknown")
                logger.info(f"  Utterance {i}: [{speaker}] {text_preview}...")
            if len(utterances) > 10:
                logger.info(f"  ... and {len(utterances) - 10} more utterances")
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
