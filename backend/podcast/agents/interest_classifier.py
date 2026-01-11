from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatOpenAI
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from typing import List, Dict
import os
import requests

class InterestClassifierAgent:
    def __init__(self, openai_api_key: str, prompt: PromptTemplate = None):
        self.llm = ChatOpenAI(api_key=openai_api_key, model="gpt-3.5-turbo")
        if prompt is None:
            self.prompt = PromptTemplate(
                input_variables=["user_interests"],
                template="""
                Here is a list of user interests: {user_interests}
                Generate a list of 3 broad categories based on the user's interests. These categories should be distinct and relatively unrelated from each other and heavily relate to the user's categories given:
                
                The topics should be outputted as <TOPIC> topic 1 </TOPIC> <TOPIC> topic 2 </TOPIC> <TOPIC> topic 3 </TOPIC>
                INCLUDE THE <TOPIC> TAGS
                """
            )
        else:
            self.prompt = prompt
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def interest_classify(self, user_interests: List[str]):
        user_interests = "\n".join(user_interests)
        return self.chain.run(user_interests=user_interests)