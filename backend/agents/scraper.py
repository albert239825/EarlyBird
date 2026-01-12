from .perplexity import PerplexityAPI
from typing import Optional, Dict, Any

class NewsScraperAgent:
    def __init__(self, perplexity_api_key: str):
        self.perplexity = PerplexityAPI(perplexity_api_key)

    def get_top_headlines(self, category: str, count: int = 1) -> Optional[Dict[str, Any]]:
        """
        Fetch one or more headlines for a category.

        When count > 1, the model is instructed to return *multiple* <HEADLINE>...</HEADLINE>
        tags so the caller can reuse them without extra API calls.
        """
        if count < 1:
            raise ValueError("count must be >= 1")

        prompt = f"""
Here is the user's topic of interest: {category}

Return the top {count} distinct headlines from current events related to the user's topic of interest.

Return ONLY the headlines, each wrapped exactly like this:
<HEADLINE>Headline text</HEADLINE>

Return exactly {count} <HEADLINE> tags and DO NOT RETURN ANY OTHER TEXT.
"""

        data = self.perplexity.perplexity_query([prompt])

        if "choices" in data and len(data["choices"]) > 0:
            return {
                "content": data["choices"][0]["message"]["content"],
                "citations": data.get("citations", []),
            }

        return None
