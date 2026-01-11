"""
Podcast generation pipeline - orchestrates AI agents to create podcasts.
"""
from backend.agents.scraper import NewsScraperAgent
from backend.agents.researcher import DeepResearchAgent
from backend.agents.script_generator import PodcastScriptGenerator
from backend.audio.generator import PodcastAudioGenerator
from backend.models.article import SimpleArticle
from backend.core.state_manager import PodcastState
from backend.utils.logging_config import get_logger
from typing import List
import os
import re
import json

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
        self.state = state

    def parse_scraper_response(self, response: str) -> str:
        """Extract headline from scraper response"""
        headlines = re.findall(r"<HEADLINE>(.*?)</HEADLINE>", response, re.DOTALL)
        list_of_headlines = [headline.strip() for headline in headlines]
        if list_of_headlines:
            return list_of_headlines[0]
        return ""
    
    def _get_articles_from_perplexity(self, num_articles: int) -> List[SimpleArticle]:
        """
        Get articles using Perplexity scraper.
        
        Args:
            num_articles: Number of articles to fetch
            
        Returns:
            List of SimpleArticle objects
        """
        articles = []
        categories = ["Technology", "Science", "Business", "World News", "Politics"]
        
        logger.info(f"Fetching {num_articles} articles from Perplexity...")
        
        for i in range(num_articles):
            category = categories[i % len(categories)]
            
            try:
                scraper_result = self.scraper.get_top_headlines(category)
                if not scraper_result or not scraper_result.get("content"):
                    logger.warning(f"Failed to get headline for category {category}, trying next...")
                    continue
                
                headline = self.parse_scraper_response(scraper_result["content"])
                if not headline:
                    logger.warning(f"Failed to parse headline, trying next...")
                    continue
                
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
    
    def generate_podcast(self) -> str:
        """
        Generate a complete podcast.
        
        Returns:
            Script text (currently empty, but structure is built)
        """
        script = ''
        num_articles = 2
        logger.info("Generating news articles using Perplexity...")
        news_articles: List[SimpleArticle] = self._get_articles_from_perplexity(num_articles=num_articles)

        # Set articles in state
        self.state.set_articles([{
            "article_data": article,
            "total_articles": num_articles
        } for article in news_articles])
        
        self.state.current_article_index = 0

        # Process each article
        news_item_index = 0
        for news_item in news_articles:
            logger.info("Conducting deep research...")
            researched_stories = self.researcher.research_stories(news_item.title, news_item.abstract)
            research_content = researched_stories[0]["research"]["choices"][0]["message"]["content"]
            
            # Update state with research
            self.state.update_article_research(news_item_index, research_content)
            self.state.update_article_script(news_item_index, {
                "to_generate_index": 0,
                "main_remaining": 5,
                "is_host": True,
                "texts": []
            })

            logger.info(f"Generating script for {news_item.title}...")

            script_generator = PodcastScriptGenerator(self.mistral_api_key)
            self.script_generators.append(script_generator)
            first_script = script_generator.generate_next_script(
                True, False, news_item, research_content, 0, 
                include_first_hello=(news_item_index == 0)
            )
            
            # Update state with script
            self.state.append_script_text(news_item_index, "host", first_script)
            self.state.increment_script_index(news_item_index)
            self.state.decrement_remaining(news_item_index)
            self.state.toggle_host(news_item_index)

            self.state.emit_articles()
            news_item_index += 1
            
        return script
   
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

    def user_ask_expert(self, question: str, filepath: str, backend_root) -> str:
        """
        Handle user asking expert a question during podcast playback.
        
        Args:
            question: User's question
            filepath: Path to the podcast file
            backend_root: Backend root directory
            
        Returns:
            Path to the generated interrupt audio file
        """
        from pathlib import Path
        
        json_file_path = Path(backend_root) / "finished_podcasts" / "podcast_metadata.json"
        
        logger.info(f"Looking for metadata file at: {json_file_path}")
        logger.info(f"Searching for filepath: {filepath}")
        
        with open(json_file_path, "r") as file:
            data = json.load(file)
            logger.info("Available filepaths in metadata:", [p.get("file_path") for p in data["metadata"]])

        i = int(filepath[filepath.rfind('.mp3') - 1])
        stories = None
        for podcast in data["metadata"]:
            if filepath in podcast["file_path"]:
                stories = podcast["stories"]
                break
                
        if stories is None:
            raise ValueError(f"No podcast found with filepath: {filepath}")

        script_generator = PodcastScriptGenerator(self.mistral_api_key)
        script_generator.chat_history.append(f"<HOST{i}>{question}</HOST{i}>")
        
        story_draft = stories[i // 2]["story"][0]['draft']
        article = SimpleArticle(title="Question", abstract=story_draft, content=story_draft)
        ans = script_generator.generate_response(
            script_generator.expert_chain, article, question, story_draft, question=True
        )

        output_dir = os.path.dirname(filepath)
        audio_generator = PodcastAudioGenerator(output_dir=output_dir)
        interrupt_path = os.path.join(output_dir, f"podcast_interrupt_{i}.mp3")
        audio_generator.generate_interrupt_response(ans, interrupt_path)
        return interrupt_path
