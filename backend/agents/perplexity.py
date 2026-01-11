from typing import List, Dict
from perplexity import Perplexity
import perplexity

class PerplexityAPI:
    def __init__(self, api_key: str):
        self.client = Perplexity(api_key=api_key)
    
    def perplexity_query(self, prompts: List[str]) -> Dict:
        """
        Query Perplexity API using official SDK.
        
        Args:
            prompts: List of prompt strings to combine into a single message
            
        Returns:
            Dict with 'choices' and 'citations' keys matching expected format
        """
        # Combine prompts (maintain current behavior)
        final_prompt = '\n'.join(prompts)
        messages = [{"role": "user", "content": final_prompt}]
        
        try:
            # Use SDK to make API call
            completion = self.client.chat.completions.create(
                model="sonar",
                messages=messages
            )
            
            # Convert SDK response to dict format for backward compatibility
            return {
                "choices": [{
                    "message": {
                        "content": completion.choices[0].message.content
                    }
                }],
                "citations": completion.citations if hasattr(completion, 'citations') and completion.citations else []
            }
        except perplexity.RateLimitError as e:
            raise Exception(f"Perplexity API rate limit exceeded: {e}")
        except perplexity.APIConnectionError as e:
            raise Exception(f"Perplexity API connection error: {e}")
        except perplexity.AuthenticationError as e:
            raise Exception(f"Perplexity API authentication error: {e}")
        except perplexity.APIStatusError as e:
            raise Exception(f"Perplexity API error (status {e.status_code}): {e}")
        except perplexity.APIError as e:
            raise Exception(f"Perplexity API error: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error calling Perplexity API: {e}")
