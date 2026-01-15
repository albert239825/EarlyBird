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

    def write_episode_script(
        self,
        stories: List[Dict[str, str]],
        max_utterances_total: int = 100,
    ) -> List[Dict[str, str]]:
        """
        Generate a full episode script (intro + stories + transitions + outro) in one call.
        """

        system = (
            "You write tight, conversational news podcast scripts in the style of NPR's Up First.\n"
            "Two speakers: host and expert.\n"
            "Tone: clear, specific, energetic but not hype; no fluff.\n"
            "\n"
            "OUTPUT FORMAT:\n"
            "- Return ONLY valid JSON (no markdown, no commentary).\n"
            '- Output must be an object with exactly one key: "utterances".\n'
            '- Each utterance must be an object with ONLY these keys: "utterance_id", "speaker", "text".\n'
            '- "speaker" must be exactly "host" or "expert".\n'
            "\n"
            "UTTERANCE STYLE:\n"
            "- Each utterance should be 2–3 sentences.\n"
            "- Aim for ~40–55 words per utterance.\n"
            "- Write for spoken audio: contractions are OK, varied sentence length, avoid long lists.\n"
            "- Avoid repeating the headline verbatim; explain it.\n"
            "\n"
            "STORY LENGTH TARGET:\n"
            "- Each story should be ~3 minutes of spoken audio (~400–500 words total per story).\n"
            "- Use quick back-and-forth pacing: alternate host/expert frequently.\n"
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

            CRITICAL FORMATTING RULES (NO EXCEPTIONS):
            - Return ONLY JSON.
            - The JSON must be an object with exactly:
            {{
                "utterances": [ ... ]
            }}
            - Each item in "utterances" must have EXACTLY these keys:
            - "utterance_id"
            - "speaker"
            - "text"
            - utterance_id must be sequential: u0, u1, u2, ...
            - speaker must be "host" or "expert" (lowercase only).
            - Maximum utterances: {max_utterances_total}

            TAG RULES (NO EXCEPTIONS):
            - Every utterance's text MUST start with exactly ONE tag, then the spoken content.
            - Allowed tags:
            - <INTRO>
            - <STORY_0>, <STORY_1>, <STORY_2>, ... (use the correct index)
            - <TRANSITION_0_1>, <TRANSITION_1_2>, ... (use the correct pair)
            - <OUTRO>
            - Do NOT put tags anywhere except the very beginning of the utterance text.
            - Do NOT include more than one tag in a single utterance.

            PACE + LENGTH TARGETS (UP FIRST STYLE):
            - Each utterance: 2–3 sentences, ~40–55 words.
            - Each story: ~400–500 total words (~3 minutes spoken).
            - Favor frequent alternation between host and expert (avoid long monologues).
            - Keep the writing concrete: what happened, why it matters now, what happens next.

            EPISODE STRUCTURE (MUST FOLLOW):
            1) Intro:
            - Create EXACTLY 1 utterance tagged <INTRO>.
            - It should preview the stories (“Coming up…”) in 2–3 sentences.

            2) Each story i:
            - Create 9–11 utterances tagged <STORY_i>.
            - The story MUST include:
            * Host: setup + stakes (why this matters today)
            * Expert: context/background (what led here)
            * Host: one pointed clarifying question
            * Expert: implications / consequences
            * Host: “what to watch next” and a clean wrap of that story
            - Within each story, alternate speakers often; do not let one speaker talk for more than 2 utterances in a row.

            3) Transitions:
            - Between story i and story i+1, create EXACTLY 1 utterance tagged <TRANSITION_i_{i+1}> spoken by the host.
            - Transition should be 1–2 sentences and should smoothly pivot to the next topic (no hard reset).

            4) Outro:
            - Create EXACTLY 1 utterance tagged <OUTRO> spoken by the host.
            - End with: “See you tomorrow.”

            EXAMPLE SHAPE (ILLUSTRATIVE ONLY):
            {{
            "utterances": [
                {{"utterance_id": "u0", "speaker": "host", "text": "<INTRO>Welcome… coming up…"}},
                {{"utterance_id": "u1", "speaker": "host", "text": "<STORY_0>Here’s what happened…"}},
                {{"utterance_id": "u2", "speaker": "expert", "text": "<STORY_0>Context…"}},
                {{"utterance_id": "u3", "speaker": "host", "text": "<TRANSITION_0_1>Alright, next…"}},
                {{"utterance_id": "u4", "speaker": "host", "text": "<STORY_1>Now to…"}},
                {{"utterance_id": "u5", "speaker": "host", "text": "<OUTRO>That’s it… See you tomorrow."}}
            ]
            }}

            EPISODE STORIES (IN ORDER):
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
        logger.info(
            f"Parsed {len(utterances) if utterances else 0} utterances from response"
        )
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
