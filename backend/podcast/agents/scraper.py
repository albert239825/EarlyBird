from .perplexity import PerplexityAPI
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatOpenAI
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from typing import List, Dict
import os
import requests

class NewsScraperAgent:
    def __init__(self, perplexity_api_key: str):
        self.perplexity = PerplexityAPI(perplexity_api_key)

    def get_top_headlines(self, category):
        prompt = f"""
        Here is the user's topic of interest: {category}
        List the top headline from current events related to the user's topic of interest ttached to this message. 
        Just return the headline in the format below: <HEADLINE>[First headline] </HEADLINE>
        DO NOT RETURN ANY OTHER TEXT
        """
        print(prompt)

        data = self.perplexity.perplexity_query([prompt])

        if "choices" in data and len(data["choices"]) > 0:
            result = {
                "content": data["choices"][0]["message"]["content"],
                "citations": data.get("citations", [])
            }
            return result
        else:
            print("Unexpected response structure:", data)
            return None