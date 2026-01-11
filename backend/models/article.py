"""
Data models for articles and news content.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Any


class SimpleArticle:
    """
    Simple article wrapper compatible with Article interface for Perplexity-sourced articles.
    
    This class represents a news article with all necessary metadata for podcast generation.
    """
    
    def __init__(self, title: str, content: str = "", abstract: str = ""):
        self.id = str(uuid.uuid4())
        self.title = title
        self.content = content if content else abstract
        self.abstract = abstract if abstract else title
        self.section = "General"
        self.lead_paragraph = abstract if abstract else title
        self.snippet = abstract if abstract else title
        self.keywords: List[str] = []
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
        self.embedding_3d: List[float] = []
        self._id = None
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, SimpleArticle):
            return False
        return self.id == other.id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary representation"""
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
    
    def __repr__(self):
        return f"SimpleArticle(id={self.id}, title='{self.title[:50]}...')"
