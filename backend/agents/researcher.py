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

class DeepResearchAgent:
    def __init__(self, perplexity_api_key: str):
        self.perplexity = PerplexityAPI(perplexity_api_key)
        
    def research_stories(self, headline: str, abstract: str) -> str:
        prompt = f"""
        The following headline and abstract is a trending news headline from the New York Times.

        Research all current news articles that provide information and context related to this topic.
        Your job is to find multiple perspectives and expert options for an UNBIASED summary of the topic.
        Focus specifically on obtaining data regarding expert opinions, related events, statistical data, future implications
        and givee specific facts and evidence to support the evidence. Your content should be a 1-2 UNBIASED 
        and very compact and dense summary of the entire topic and story.
         
        Your results will be used by a downstream
        AI agent, so much sure to output the results and NOTHING ELSE but the results. 

        <HEADLINE>{headline}</HEADLINE>
        <ABSTRACT>{abstract}</ABSTRACT>
        """

        research = self.perplexity.perplexity_query([prompt])
        researched_stories = [{"headline": headline, "research": research}]
        return researched_stories
