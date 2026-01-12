"""
Podcast generation pipeline - orchestrates AI agents to create podcasts.
"""
from backend.agents.scraper import NewsScraperAgent
from backend.agents.researcher import DeepResearchAgent
from backend.agents.script_generator import PodcastScriptGenerator
from backend.agents.openai_script_writer import OpenAIScriptWriter
from backend.audio.generator import PodcastAudioGenerator
from backend.models.article import SimpleArticle
from backend.core.state_manager import PodcastState
from backend.utils.logging_config import get_logger
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import Counter
import random
import os
import re
import json
import uuid

logger = get_logger(__name__)


class PodcastPipeline:
    """Orchestrates the podcast generation workflow"""
    
    def __init__(
        self,
        perplexity_api_key: str,
        openai_api_key: str,
        mistral_api_key: str,
        state: PodcastState
    ):
        """
        Initialize the podcast pipeline.
        
        Args:
            perplexity_api_key: API key for Perplexity
            openai_api_key: API key for OpenAI
            mistral_api_key: API key for Mistral
            state: PodcastState instance for managing generation state
        """
        self.scraper = NewsScraperAgent(perplexity_api_key)
        self.researcher = DeepResearchAgent(perplexity_api_key)
        self.script_generators = []
        self.mistral_api_key = mistral_api_key
        self.openai_script_writer = OpenAIScriptWriter(openai_api_key)
        self.state = state

    def parse_scraper_response(self, response: str) -> str:
        """Extract headline from scraper response"""
        headlines = self.parse_headlines(response)
        return headlines[0] if headlines else ""

    def parse_headlines(self, response: str) -> List[str]:
        """Extract all <HEADLINE>...</HEADLINE> blocks from a scraper response."""
        if not response:
            return []
        headlines = re.findall(r"<HEADLINE>(.*?)</HEADLINE>", response, re.DOTALL)
        return [h.strip() for h in headlines if h and h.strip()]

    _UTTERANCE_TAG_RE = re.compile(
        r"^<(INTRO|OUTRO|STORY_(\d+)|TRANSITION_(\d+)_(\d+))>\s*",
        re.DOTALL,
    )

    def _split_episode_utterances(
        self,
        utterances: List[Dict[str, str]],
        num_stories: int,
    ) -> Dict[str, Any]:
        """
        Split a tagged episode utterance list into:
          - intro_utterances
          - outro_utterances
          - story_utterances_by_index (with TRANSITION_a_b prepended to story b)

        Tags are stripped from text.
        """
        intro: List[Dict[str, str]] = []
        outro: List[Dict[str, str]] = []
        stories: List[List[Dict[str, str]]] = [[] for _ in range(num_stories)]
        transitions_to_prepend: List[List[Dict[str, str]]] = [[] for _ in range(num_stories)]

        current_story = 0

        for u in utterances or []:
            if not isinstance(u, dict):
                continue
            speaker = u.get("speaker")
            text = u.get("text")
            if speaker not in ("host", "expert"):
                continue
            if not isinstance(text, str) or not text.strip():
                continue

            m = self._UTTERANCE_TAG_RE.match(text.strip())
            tag_story_index: Optional[int] = None
            transition_to_index: Optional[int] = None

            stripped = text.strip()
            if m:
                # Groups:
                # 1: INTRO|OUTRO|STORY_i|TRANSITION_a_b
                # 2: story_i index
                # 3: transition a
                # 4: transition b
                stripped = self._UTTERANCE_TAG_RE.sub("", stripped, count=1).strip()
                if m.group(1) == "INTRO":
                    intro.append({"speaker": speaker, "text": stripped})
                    continue
                if m.group(1) == "OUTRO":
                    outro.append({"speaker": speaker, "text": stripped})
                    continue
                if m.group(2) is not None:
                    tag_story_index = int(m.group(2))
                if m.group(3) is not None and m.group(4) is not None:
                    transition_to_index = int(m.group(4))
            else:
                # Missing tag: default to current story bucket.
                logger.warning("Utterance missing tag; defaulting to current story bucket")

            if transition_to_index is not None:
                if 0 <= transition_to_index < num_stories:
                    transitions_to_prepend[transition_to_index].append(
                        {"speaker": speaker, "text": stripped}
                    )
                    continue
                logger.warning(
                    f"Transition targets invalid story index {transition_to_index}; dropping"
                )
                continue

            if tag_story_index is not None:
                if 0 <= tag_story_index < num_stories:
                    current_story = tag_story_index
                    stories[tag_story_index].append({"speaker": speaker, "text": stripped})
                    continue
                logger.warning(f"Story tag index out of range: {tag_story_index}; dropping")
                continue

            # Fallback: current story
            if 0 <= current_story < num_stories:
                stories[current_story].append({"speaker": speaker, "text": stripped})

        # Prepend transitions to destination stories
        for i in range(num_stories):
            if transitions_to_prepend[i]:
                stories[i] = transitions_to_prepend[i] + stories[i]

        # Assign per-file sequential utterance_id fields (matching existing shape)
        def _with_ids(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
            out: List[Dict[str, str]] = []
            for idx, item in enumerate(items):
                out.append(
                    {
                        "utterance_id": f"u{idx}",
                        "speaker": item["speaker"],
                        "text": item["text"],
                    }
                )
            return out

        return {
            "intro_utterances": _with_ids(intro),
            "outro_utterances": _with_ids(outro),
            "story_utterances_by_index": [_with_ids(s) for s in stories],
        }
    
    def _get_articles_from_perplexity(
        self,
        num_articles: int,
        categories: Optional[List[Optional[str]]] = None,
    ) -> List[SimpleArticle]:
        """
        Get articles using Perplexity scraper.
        
        Args:
            num_articles: Number of articles to fetch
            categories: Optional list of categories per story index. If an element is None,
              a random category will be selected for that story.
            
        Returns:
            List of SimpleArticle objects
        """
        articles: List[SimpleArticle] = []
        default_categories = ["Technology", "Science", "Business", "World News", "Politics"]
        
        logger.info(f"Fetching {num_articles} articles from Perplexity...")

        # Resolve per-story categories (preserve old behavior when categories is None)
        resolved_categories: List[str] = []
        if categories is None:
            for i in range(num_articles):
                resolved_categories.append(default_categories[i % len(default_categories)])
        else:
            for i in range(num_articles):
                cat = categories[i] if i < len(categories) else None
                if cat is None:
                    resolved_categories.append(random.choice(default_categories))
                else:
                    resolved_categories.append(str(cat))

        # Count how many headlines we need per category so duplicates can be satisfied
        needed_per_category = Counter(resolved_categories)

        # Cache of headlines to avoid repeat API calls for duplicate categories
        headline_cache: Dict[str, List[str]] = {}

        for i, category in enumerate(resolved_categories):
            try:
                if category not in headline_cache:
                    need = max(1, int(needed_per_category.get(category, 1)))
                    scraper_result = self.scraper.get_top_headlines(category, count=need)
                    if not scraper_result or not scraper_result.get("content"):
                        logger.warning(f"Failed to get headline(s) for category {category}, using placeholder...")
                        headline_cache[category] = []
                    else:
                        parsed = self.parse_headlines(scraper_result["content"])
                        if len(parsed) < need:
                            logger.warning(
                                f"Only got {len(parsed)}/{need} headlines for category '{category}'. "
                                "Padding with placeholders to avoid extra API calls."
                            )
                            parsed = parsed + [
                                f"Top {category} Story {j + 1}"
                                for j in range(len(parsed), need)
                            ]
                        headline_cache[category] = parsed

                # Pop next headline for this category (duplicate-safe)
                headline_list = headline_cache.get(category) or []
                headline = headline_list.pop(0) if headline_list else ""
                if not headline:
                    headline = f"Top {category} Story {i + 1}"
                
                article = SimpleArticle(title=headline, abstract=headline)
                articles.append(article)
                logger.info(f"Fetched article {i+1}/{num_articles}: {headline[:50]}...")
                
            except Exception as e:
                logger.error(f"Error fetching article {i+1}: {e}")
                continue
        
        # Fill in with placeholder articles if needed
        while len(articles) < num_articles:
            article = SimpleArticle(
                title=f"Top News Story {len(articles) + 1}",
                abstract="Current news story from Perplexity"
            )
            articles.append(article)
        
        return articles[:num_articles]
    
    # def generate_podcast(self) -> str:
    #     """
    #     Generate a complete podcast.
        
    #     Returns:
    #         Script text (currently empty, but structure is built)
    #     """
    #     script = ''
    #     num_articles = 2
    #     logger.info("Generating news articles using Perplexity...")
    #     news_articles: List[SimpleArticle] = self._get_articles_from_perplexity(num_articles=num_articles)

    #     # Set articles in state
    #     self.state.set_articles([{
    #         "article_data": article,
    #         "total_articles": num_articles
    #     } for article in news_articles])
        
    #     self.state.current_article_index = 0

    #     # Process each article
    #     news_item_index = 0
    #     for news_item in news_articles:
    #         logger.info("Conducting deep research...")
    #         researched_stories = self.researcher.research_stories(news_item.title, news_item.abstract)
    #         research_content = researched_stories[0]["research"]["choices"][0]["message"]["content"]
            
    #         # Update state with research
    #         self.state.update_article_research(news_item_index, research_content)
    #         self.state.update_article_script(news_item_index, {
    #             "to_generate_index": 0,
    #             "main_remaining": 5,
    #             "is_host": True,
    #             "texts": []
    #         })

    #         logger.info(f"Generating script for {news_item.title}...")

    #         script_generator = PodcastScriptGenerator(self.mistral_api_key)
    #         self.script_generators.append(script_generator)
    #         first_script = script_generator.generate_next_script(
    #             True, False, news_item, research_content, 0, 
    #             include_first_hello=(news_item_index == 0)
    #         )
            
    #         # Update state with script
    #         self.state.append_script_text(news_item_index, "host", first_script)
    #         self.state.increment_script_index(news_item_index)
    #         self.state.decrement_remaining(news_item_index)
    #         self.state.toggle_host(news_item_index)

    #         self.state.emit_articles()
    #         news_item_index += 1
            
    #     return script

    def generate_research_and_script_assets(
        self,
        podcast_dir: Path,
        num_articles: int = 2,
        categories: Optional[List[Optional[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Phase 1: generate and persist research docs + HQ script utterances (no TTS).
        Writes:
          - <podcast_dir>/podcast.json
          - <podcast_dir>/research/story_<i>.md
          - <podcast_dir>/script/story_<i>.json
        """
        podcast_dir.mkdir(parents=True, exist_ok=True)
        research_dir = podcast_dir / "research"
        script_dir = podcast_dir / "script"
        research_dir.mkdir(parents=True, exist_ok=True)
        script_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Generating news articles using Perplexity...")
        news_articles: List[SimpleArticle] = self._get_articles_from_perplexity(
            num_articles=num_articles,
            categories=categories,
        )

        # Update state early so clients can render placeholders
        self.state.set_articles([{
            "article_data": article,
            "total_articles": num_articles
        } for article in news_articles])
        self.state.current_article_index = 0
        self.state.emit_articles()

        stories_meta: List[Dict[str, Any]] = []
        story_inputs_for_episode: List[Dict[str, str]] = []

        for story_index, story in enumerate(news_articles):
            logger.info(f"[story {story_index}] Researching via Perplexity...")
            researched = self.researcher.research_stories(story.title, story.abstract)
            research_payload = researched[0]["research"]
            research_text = research_payload["choices"][0]["message"]["content"]
            citations = research_payload.get("citations", [])

            research_md = "\n".join([
                "## Core_summary",
                research_text.strip(),
                "",
                "## Key_facts",
                "",
                "## Q_and_A_additions",
                "",
                "## Citations",
                "\n".join(f"- {c}" for c in citations) if citations else "- (none)",
                "",
            ])

            (research_dir / f"story_{story_index}.md").write_text(research_md, encoding="utf-8")

            # Update state with research (for UI)
            self.state.update_article_research(story_index, research_text)
            self.state.emit_articles()

            # Collect inputs for a single episode-level script generation call.
            story_inputs_for_episode.append(
                {
                    "headline": story.title,
                    "research_md": research_md,
                    # optional: categories aren't currently persisted per story elsewhere
                    "category": (categories[story_index] if categories and story_index < len(categories) else "") or "",
                }
            )

            stories_meta.append({
                "story_index": story_index,
                "title": story.title,
            })

        # Episode-level script generation
        logger.info("Writing full episode script via OpenAI (single call)...")
        episode_utterances = self.openai_script_writer.write_episode_script(
            stories=story_inputs_for_episode,
        )
        split = self._split_episode_utterances(
            utterances=episode_utterances,
            num_stories=num_articles,
        )

        # Write intro/outro script files (if present)
        intro_utterances = split["intro_utterances"]
        outro_utterances = split["outro_utterances"]

        if intro_utterances:
            (script_dir / "intro.json").write_text(
                json.dumps({"story_index": -1, "utterances": intro_utterances}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        if outro_utterances:
            (script_dir / "outro.json").write_text(
                json.dumps({"story_index": -2, "utterances": outro_utterances}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Write per-story scripts (with transitions prepended to destination story)
        story_utterances_by_index: List[List[Dict[str, str]]] = split["story_utterances_by_index"]
        for story_index, utterances in enumerate(story_utterances_by_index):
            script_obj = {"story_index": story_index, "utterances": utterances}
            (script_dir / f"story_{story_index}.json").write_text(
                json.dumps(script_obj, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            # Update state with a compatible structure for current clients
            self.state.update_article_script(
                story_index,
                {
                    "to_generate_index": len(utterances),
                    "main_remaining": 0,
                    "is_host": True,
                    "utterances": utterances,
                    "texts": [{"role": u["speaker"], "content": u["text"]} for u in utterances],
                },
            )
            self.state.emit_articles()

        podcast_json = {
            "podcast_id": podcast_dir.name,
            "stories": stories_meta,
        }
        (podcast_dir / "podcast.json").write_text(
            json.dumps(podcast_json, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return podcast_json
    
    def generate_audio_segments_and_manifest(self, podcast_dir: Path, audio_generator: PodcastAudioGenerator) -> Dict[str, Any]:
        """
        Phase 2: generate audio segments from utterances and create manifest.json.
        
        Reads script/*.json files, generates MP3 segments, and creates manifest.json.
        """
        script_dir = podcast_dir / "script"
        audio_pregen_dir = podcast_dir / "audio" / "pregen"
        audio_pregen_dir.mkdir(parents=True, exist_ok=True)
        
        segments: List[Dict[str, Any]] = []
        segment_counter = 1
        
        # Load script files in order: intro -> stories -> outro
        script_files: List[Path] = []
        intro_path = script_dir / "intro.json"
        outro_path = script_dir / "outro.json"
        if intro_path.exists():
            script_files.append(intro_path)
        story_files = sorted(script_dir.glob("story_*.json"))
        script_files.extend(story_files)
        if outro_path.exists():
            script_files.append(outro_path)

        logger.info(f"Generating audio segments from {len(script_files)} script files...")
        
        for script_file in script_files:
            script_data = json.loads(script_file.read_text(encoding="utf-8"))
            story_index = script_data.get("story_index")
            if story_index is None:
                # Backward compatibility: if missing, infer from filename.
                name = script_file.name
                if name.startswith("story_") and name.endswith(".json"):
                    try:
                        story_index = int(name[len("story_") : -len(".json")])
                    except Exception:
                        story_index = -999
                elif name == "intro.json":
                    story_index = -1
                elif name == "outro.json":
                    story_index = -2
                else:
                    story_index = -999
            utterances = script_data["utterances"]
            
            for utterance in utterances:
                segment_id = f"seg_{segment_counter:04d}"
                utterance_id = utterance["utterance_id"]
                speaker = utterance["speaker"]
                text = utterance["text"]
                
                # Generate MP3 segment
                segment_path = audio_pregen_dir / f"{segment_id}.mp3"
                duration_ms = audio_generator.generate_segment(
                    speaker=speaker,
                    text=text,
                    output_path=str(segment_path)
                )
                
                # Add to manifest
                segments.append({
                    "segment_id": segment_id,
                    "utterance_id": utterance_id,
                    "story_index": story_index,
                    "speaker": speaker,
                    "text": text,
                    "url": f"/podcasts/{podcast_dir.name}/segments/{segment_id}",
                    "duration_ms": duration_ms,
                    "source": "pregen"
                })
                
                segment_counter += 1
                logger.info(f"Generated segment {segment_id} ({speaker}): {text[:50]}...")
        
        manifest = {
            "podcast_id": podcast_dir.name,
            "segments": segments
        }
        
        logger.info(f"Generated {len(segments)} audio segments")
        return manifest
   
    def generate_next_part_podcast(self, index: int) -> str:
        """
        Generate the next part of a podcast script.
        
        Args:
            index: Article index
            
        Returns:
            Generated script text
        """
        article_obj = self.state.get_article(index)
        if not article_obj:
            raise ValueError(f"No article found at index {index}")
            
        article_data = article_obj["article_data"]
        research_data = article_obj["research"]
        is_host = article_obj["script"]["is_host"]
        to_generate_index = article_obj["script"]["to_generate_index"]
        remaining = article_obj["script"]["main_remaining"]
        
        first_script = self.script_generators[index].generate_next_script(
            is_host, remaining==1, article_data, research_data, to_generate_index, False
        )
        
        # Update state
        role = "host" if is_host else "expert"
        self.state.append_script_text(index, role, first_script)
        self.state.increment_script_index(index)
        self.state.decrement_remaining(index)
        self.state.toggle_host(index)
        self.state.emit_articles()

        return first_script

    def answer_question(self, question: str, index: int) -> str:
        """
        Answer a user question about an article.
        
        Args:
            question: User's question
            index: Article index
            
        Returns:
            Answer text
        """
        article_obj = self.state.get_article(index)
        if not article_obj:
            raise ValueError(f"No article found at index {index}")
            
        article_data = article_obj["article_data"]
        research_data = article_obj["research"]

        response = self.script_generators[index].answer_question(article_data, research_data, question)
        return response

    # def user_ask_expert(self, question: str, filepath: str, backend_root) -> str:
    #     """
    #     Handle user asking expert a question during podcast playback.
        
    #     Args:
    #         question: User's question
    #         filepath: Path to the podcast file
    #         backend_root: Backend root directory
            
    #     Returns:
    #         Path to the generated interrupt audio file
    #     """
    #     from pathlib import Path
        
    #     json_file_path = Path(backend_root) / "finished_podcasts" / "podcast_metadata.json"
        
    #     logger.info(f"Looking for metadata file at: {json_file_path}")
    #     logger.info(f"Searching for filepath: {filepath}")
        
    #     with open(json_file_path, "r") as file:
    #         data = json.load(file)
    #         logger.info("Available filepaths in metadata:", [p.get("file_path") for p in data["metadata"]])

    #     i = int(filepath[filepath.rfind('.mp3') - 1])
    #     stories = None
    #     for podcast in data["metadata"]:
    #         if filepath in podcast["file_path"]:
    #             stories = podcast["stories"]
    #             break
                
    #     if stories is None:
    #         raise ValueError(f"No podcast found with filepath: {filepath}")

    #     script_generator = PodcastScriptGenerator(self.mistral_api_key)
    #     script_generator.chat_history.append(f"<HOST{i}>{question}</HOST{i}>")
        
    #     story_draft = stories[i // 2]["story"][0]['draft']
    #     article = SimpleArticle(title="Question", abstract=story_draft, content=story_draft)
    #     ans = script_generator.generate_response(
    #         script_generator.expert_chain, article, question, story_draft, question=True
    #     )

    #     output_dir = os.path.dirname(filepath)
    #     audio_generator = PodcastAudioGenerator(output_dir=output_dir)
    #     interrupt_path = os.path.join(output_dir, f"podcast_interrupt_{i}.mp3")
    #     audio_generator.generate_interrupt_response(ans, interrupt_path)
    #     return interrupt_path
