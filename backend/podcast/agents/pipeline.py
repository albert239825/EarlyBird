from .scraper import NewsScraperAgent
from .researcher import DeepResearchAgent
from .script_generator import PodcastScriptGenerator
from .audio.audio_generation import PodcastAudioGenerator
from typing import List
import os
import re
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

from backend.podcast.AppData import data as app_data

load_dotenv()


class SimpleArticle:
    """Simple article wrapper compatible with Article interface for Perplexity-sourced articles"""
    def __init__(self, title: str, content: str = "", abstract: str = ""):
        self.id = str(uuid.uuid4())
        self.title = title
        self.content = content if content else abstract
        self.abstract = abstract if abstract else title
        self.section = "General"
        self.lead_paragraph = abstract if abstract else title
        self.snippet = abstract if abstract else title
        self.keywords = []
        self.url = ""
        self.date = datetime.now().isoformat()
        self.all_data = {
            "headline": {"main": title},
            "lead_paragraph": self.lead_paragraph,
            "abstract": self.abstract,
            "snippet": self.snippet,
            "keywords": [],
            "web_url": "",
            "section_name": self.section,
            "pub_date": self.date,
            "document_type": "article"
        }
        self.interest_score = 0
        self.embedding_3d = []
        self._id = None
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return self.id == other.id
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "abstract": self.abstract,
            "section": self.section,
            "lead_paragraph": self.lead_paragraph,
            "snippet": self.snippet,
            "keywords": self.keywords,
            "url": self.url,
            "date": self.date,
            "all_data": self.all_data,
            "interest_score": self.interest_score,
        }


class NewsPodcastPipeline:
    def __init__(
        self,
        perplexity_api_key: str,
        openai_api_key: str,
        mistral_api_key: str
    ):
        self.scraper = NewsScraperAgent(perplexity_api_key)
        self.researcher = DeepResearchAgent(perplexity_api_key)
        self.script_generators = []

    def parse_scraper_response(self, response: str) -> str:
        headlines = re.findall(r"<HEADLINE>(.*?)</HEADLINE>", response, re.DOTALL)
        list_of_headlines = [headline.strip() for headline in headlines]
        if list_of_headlines:
            return list_of_headlines[0]
        return ""
    
    def _get_articles_from_perplexity(self, num_articles: int) -> List[SimpleArticle]:
        """Get articles using Perplexity scraper instead of ML model"""
        articles = []
        categories = ["Technology", "Science", "Business", "World News", "Politics"]
        
        print(f"Fetching {num_articles} articles from Perplexity...")
        
        for i in range(num_articles):
            category = categories[i % len(categories)]
            
            try:
                scraper_result = self.scraper.get_top_headlines(category)
                if not scraper_result or not scraper_result.get("content"):
                    print(f"Failed to get headline for category {category}, trying next...")
                    continue
                
                headline = self.parse_scraper_response(scraper_result["content"])
                if not headline:
                    print(f"Failed to parse headline, trying next...")
                    continue
                
                article = SimpleArticle(title=headline, abstract=headline)
                articles.append(article)
                print(f"Fetched article {i+1}/{num_articles}: {headline[:50]}...")
                
            except Exception as e:
                print(f"Error fetching article {i+1}: {e}")
                continue
        
        while len(articles) < num_articles:
            article = SimpleArticle(
                title=f"Top News Story {len(articles) + 1}",
                abstract="Current news story from Perplexity"
            )
            articles.append(article)
        
        return articles[:num_articles]
    
    def generate_podcast(self) -> str:
        script = ''
        num_articles = 2
        print("Generating news articles using Perplexity...")
        news_articles: List[SimpleArticle] = self._get_articles_from_perplexity(num_articles=num_articles)

        app_data["Articles"] = [{
            "article_data": article,
            "total_articles": num_articles
            }
            for article in news_articles
        ]

        app_data["current_article"] = 0

        news_item_index = 0
        for news_item in news_articles:
            print("Conducting deep research...")
            researched_stories = self.researcher.research_stories(news_item.title, news_item.abstract)
            research_content = researched_stories[0]["research"]["choices"][0]["message"]["content"]
            app_data["Articles"][news_item_index]["research"] = research_content
            app_data["Articles"][news_item_index]["script"] = {
                "to_generate_index": 0,
                "main_remaining": 5,
                "is_host": True,
                "texts": []
            }

            print(f"Generating script for {news_item.title}...")

            mistral_api_key = os.getenv("MISTRAL_API_KEY")
            script_generator = PodcastScriptGenerator(mistral_api_key)
            self.script_generators.append(script_generator)
            first_script = script_generator.generate_next_script(True, False, news_item, research_content, 0, include_first_hello=(news_item_index == 0))
            app_data["Articles"][news_item_index]["script"]["texts"].append({
                "role": "host",
                "content": first_script
            })
            app_data["Articles"][news_item_index]["script"]["to_generate_index"] = 1
            app_data["Articles"][news_item_index]["script"]["main_remaining"] -= 1
            app_data["Articles"][news_item_index]["script"]["is_host"] = False

            app_data["emit_articles"]()
            news_item_index += 1
            
        return script
   
    def generate_next_part_podcast(self, index: int) -> str:
        article_obj = app_data["Articles"][index]
        article_data = article_obj["article_data"]
        research_data = article_obj["research"]
        is_host = article_obj["script"]["is_host"]
        to_generate_index = article_obj["script"]["to_generate_index"]
        remaining = article_obj["script"]["main_remaining"]
        
        first_script = self.script_generators[index].generate_next_script(is_host, remaining==1, article_data, research_data, to_generate_index, False)
        app_data["Articles"][index]["script"]["texts"].append({
            "role": "host" if is_host else "expert",
            "content": first_script
        })

        app_data["Articles"][index]["script"]["to_generate_index"] += 1
        app_data["Articles"][index]["script"]["main_remaining"] -= 1
        app_data["Articles"][index]["script"]["is_host"] = not is_host

        app_data["emit_articles"]()

        return first_script

    def answer_question(self, question: str, index: int) -> str:
        article_obj = app_data["Articles"][index]
        article_data = article_obj["article_data"]
        research_data = article_obj["research"]

        response = self.script_generators[index].answer_question(article_data, research_data, question)
        return response

    def user_ask_expert(self, question: str, filepath: str) -> str:
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        json_file_path = os.path.join(
            self.project_root,
            'backend',
            'podcast',
            'finished_podcasts',
            'podcast_metadata.json'
        )
        
        print(f"Looking for metadata file at: {json_file_path}")
        print(f"Searching for filepath: {filepath}")
        
        with open(json_file_path, "r") as file:
            data = json.load(file)
            print("Available filepaths in metadata:", [p.get("file_path") for p in data["metadata"]])

        i = int(filepath[filepath.rfind('.mp3') - 1])
        stories = None
        for podcast in data["metadata"]:
            if filepath in podcast["file_path"]:
                stories = podcast["stories"]
                break
                
        if stories is None:
            raise ValueError(f"No podcast found with filepath: {filepath}")

        mistral_api_key = os.getenv("MISTRAL_API_KEY")
        script_generator = PodcastScriptGenerator(mistral_api_key)
        script_generator.chat_history.append(f"<HOST{i}>{question}</HOST{i}>")
        
        story_draft = stories[i // 2]["story"][0]['draft']
        article = SimpleArticle(title="Question", abstract=story_draft, content=story_draft)
        ans = script_generator.generate_response(script_generator.expert_chain, article, question, story_draft, question=True)

        output_dir = os.path.dirname(filepath)
        audio_generator = PodcastAudioGenerator(output_dir=output_dir)
        interrupt_path = os.path.join(output_dir, f"podcast_interrupt_{i}.mp3")
        audio_generator.generate_interrupt_response(ans, interrupt_path)
        return interrupt_path
