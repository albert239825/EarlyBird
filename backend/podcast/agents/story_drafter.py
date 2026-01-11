from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatOpenAI
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from typing import List, Dict
import os
import requests

class StoryDrafterAgent:
    def __init__(self, openai_api_key: str, prompt: PromptTemplate = None):
        self.llm = ChatOpenAI(api_key=openai_api_key, model="gpt-4o-mini")
        if prompt is None:
            self.prompt = PromptTemplate(
                input_variables=["story_data"],
                template="""
                Draft a compelling story based on this research:
                {story_data}
                Include a hook to grab attention, a clear narrative structure, key points and analysis, engaging transitions, and thought-provoking conclusions.
                Ensure all the facts and evidence related to the story from the research are incorporated in a coherent and engaging manner and remain in the story.
                ONLY OUTPUT THE STORY PRODUCED BASED ON THE RESEARCH. DO NOT RETURN ANY OTHER TEXT.
                """
            )
        else:
            self.prompt = prompt
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def draft_stories(self, researched_stories: str) -> List[Dict]:
        drafted_stories = []
        draft = self.chain.run(story_data=researched_stories)
        drafted_stories.append({"draft": draft})
        return drafted_stories