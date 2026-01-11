"""
State management for podcast generation.
Replaces the global AppData dict with a proper class-based approach.
"""
from typing import List, Dict, Any, Optional, Callable


class PodcastState:
    """
    Encapsulates podcast generation state.
    
    This class manages the state of ongoing podcast generation, including articles,
    scripts, and WebSocket communication. It replaces the previous global dict pattern
    with a testable, type-safe class.
    """
    
    def __init__(self, socketio=None):
        """
        Initialize podcast state.
        
        Args:
            socketio: Flask-SocketIO instance for real-time updates
        """
        self.socketio = socketio
        self.articles: List[Dict[str, Any]] = []
        self.current_article_index: int = 0
        self._emit_function: Optional[Callable] = None
        self._emit_articles_function: Optional[Callable] = None
    
    def set_emit_function(self, func: Callable):
        """Set the function used to emit WebSocket messages"""
        self._emit_function = func
    
    def set_emit_articles_function(self, func: Callable):
        """Set the function used to emit article updates"""
        self._emit_articles_function = func
    
    def emit_update(self, message_type: str, data: Any):
        """
        Emit WebSocket updates to connected clients.
        
        Args:
            message_type: Type of message being sent
            data: Data payload to send
        """
        if self._emit_function and self.socketio:
            self._emit_function(self.socketio, {"message": message_type, "data": data})
    
    def emit_articles(self):
        """Emit current articles state to connected clients"""
        if self._emit_articles_function:
            self._emit_articles_function()
    
    def add_article(self, article_data: Any, total_articles: int):
        """
        Add an article to the state.
        
        Args:
            article_data: Article object (SimpleArticle)
            total_articles: Total number of articles being processed
        """
        self.articles.append({
            "article_data": article_data,
            "total_articles": total_articles
        })
    
    def set_articles(self, articles: List[Dict[str, Any]]):
        """Set all articles at once"""
        self.articles = articles
    
    def get_article(self, index: int) -> Optional[Dict[str, Any]]:
        """Get article at specific index"""
        if 0 <= index < len(self.articles):
            return self.articles[index]
        return None
    
    def update_article_research(self, index: int, research: str):
        """Update research content for an article"""
        if 0 <= index < len(self.articles):
            self.articles[index]["research"] = research
    
    def update_article_script(self, index: int, script_data: Dict[str, Any]):
        """Update script data for an article"""
        if 0 <= index < len(self.articles):
            self.articles[index]["script"] = script_data
    
    def append_script_text(self, index: int, role: str, content: str):
        """Append text to an article's script"""
        if 0 <= index < len(self.articles) and "script" in self.articles[index]:
            self.articles[index]["script"]["texts"].append({
                "role": role,
                "content": content
            })
    
    def increment_script_index(self, index: int):
        """Increment the to_generate_index for an article's script"""
        if 0 <= index < len(self.articles) and "script" in self.articles[index]:
            self.articles[index]["script"]["to_generate_index"] += 1
    
    def decrement_remaining(self, index: int):
        """Decrement the main_remaining counter for an article's script"""
        if 0 <= index < len(self.articles) and "script" in self.articles[index]:
            self.articles[index]["script"]["main_remaining"] -= 1
    
    def toggle_host(self, index: int):
        """Toggle the is_host flag for an article's script"""
        if 0 <= index < len(self.articles) and "script" in self.articles[index]:
            current = self.articles[index]["script"].get("is_host", True)
            self.articles[index]["script"]["is_host"] = not current
    
    def clear(self):
        """Clear all state"""
        self.articles = []
        self.current_article_index = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary representation"""
        return {
            "articles": self.articles,
            "current_article_index": self.current_article_index
        }


# Global instance for backward compatibility during migration
# This will be replaced with proper dependency injection
_global_state: Optional[PodcastState] = None


def get_global_state() -> PodcastState:
    """Get the global state instance (for migration purposes)"""
    global _global_state
    if _global_state is None:
        _global_state = PodcastState()
    return _global_state


def set_global_state(state: PodcastState):
    """Set the global state instance"""
    global _global_state
    _global_state = state
