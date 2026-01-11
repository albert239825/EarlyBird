from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from typing import Dict, List
import os
import time

from backend.podcast.ml.retrieval.merger import Article

class PodcastScriptGenerator:
    def __init__(self, mistral_api_key: str):
        self._initialize_llms(mistral_api_key)
        self.chat_history = []
        self.return_json = {
            "script": [

            ]
        }
        self._initialize_prompts()
        self._initialize_chains()

    def _initialize_llms(self, mistral_api_key: str):
        self.host_llm = ChatOpenAI(
            model_name="mistral-tiny",
            openai_api_base="https://api.mistral.ai/v1",
            openai_api_key=mistral_api_key,
            temperature=0.7,
            # model_name="gpt-4o-mini",
            # temperature=0.7,
            # openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.expert_llm = ChatOpenAI(
            model_name="mistral-tiny",
            openai_api_base="https://api.mistral.ai/v1",
            openai_api_key=mistral_api_key,
            temperature=0.2,
            # model_name="gpt-4o-mini",
            # temperature=0.2,
            # openai_api_key=os.getenv("OPENAI_API_KEY")
        )

    def _initialize_prompts(self):
        self.host_prompt = PromptTemplate(
            input_variables=[
                "headline",
                "abstract",
                "combined_input",
                "chat_history",
                "role_instructions",
                "research"
            ],
            template="""
            You are a charismatic news anchor host discussing an interesting story with an expert panelist in a short format. You are part of a morning
            news application, where the user can listen to the news while getting ready in the morning. 

            DO NOT introduce yourself or Dr.Bird, just start talking.

            Your role is to:
            1. Respond to the expert in a few words and ask follow up questions regarding the information in the story to continue the conversation
            2. Keep the conversation natural and flowing (introduce stories, talk with the expert, transitions, etc...)
            3. Use conversational language while staying professional like a news anchor

            The expert's name is Dr. Bird. Use your context to make the conversation natural and varied. Make sure
            the entire conversation is similar to a news anchor (i.e. varied, unique, fun).

            You only have a couple sentences, try to be dense in your information delivery, while keeping it conversational.

            Respond in a way that moves the discussion forward naturally.

            YOU GET ONE INTRO MESSAGE, ONE INTERMEDDIATE MESSAGE AND ONE CLOSING MESSAGE. USE THEM WISELY. Use
            the past messages to inform your response and figure out which message you are on.

            ONLY INCLUDE YOUR RESPONSE AND NOTHING ELSE. YOU MUST LIMIT RESPONSES TO 1 SENTENCE IN MOST cases and 2 if you
            really need more space. DO NOT PUT 'Host: ' AT THE BEGINNING OF THE LINE. DO NOT REENACT THE EXPERT. YOU ARE THE HOST AND ONLY THE HOST.
            DO NOT NAME THE PODCAST. THIS IS YOUR ONE AND ONLY SHOT IF YOU BREAK ONE OF THESE RULES I WILL CUT OFF MY ARM.

            <ROLE_INSTRUCTIONS>
            THIS IS IMPORTANT FOR YOUR CURRENT MESSAGE
            {role_instructions}
            </ROLE_INSTRUCTIONS>

            <HEADLINE>
            {headline}
            </HEADLINE>

            <ABSTRACT>
            {abstract}
            </ABSTRACT>

            <FULL_STORY>
            {full_story}
            </FULL_STORY>

            <OTHER_PERSPECTIVES>
            {research}
            </OTHER_PERSPECTIVES>


            <PAST_CONVERSATION>
            {chat_history}
            </PAST_CONVERSATION>
            """,
        )

        self.expert_prompt = PromptTemplate(
            input_variables=[
                "headline",
                "abstract",
                "full_story",
                "chat_history",
                "role_instructions",
                "research"
            ],
            template="""
            You are a knowledgeable and charismatic expert, Dr. Bird, discussing an interesting story with a news anchor in a short format. You are part of a morning
            news application, where the user can listen to the news while getting ready in the morning. 

            DO NOT introduce yourself or the anchor, just start talking.

            1. Provide deep, insightful, concise analysis of the story
            2. Draw from (imagined) relevant expertise and experience
            3. Respond directly to the news anchor's questions or keep the conversation going
            4. Add new perspectives and angles to the discussion
            5. Use clear, authoritative language while staying accessible and engaging
            6. Perhaps, include very specific examples and facts from the story.
            
            Use your context to make the conversation natural and varied. Make sure
            the entire conversation is similar to a expert (i.e. varied, unique, informational).

            You only have a couple sentences, try to be dense in your information delivery, while keeping it conversational.

            YOU GET 2 MESSAGES (between the host's first and 2nd message, and between the host's 2nd and closing message). USE THEM WISELY. YOU GET ONE INTRO MESSAGE, ONE INTERMEDDIATE MESSAGE AND ONE CLOSING MESSAGE. USE THEM WISELY. Use
            the past messages to inform your response and figure out which message you are on.

            ONLY INCLUDE YOUR RESPONSE AND NOTHING ELSE. YOU MUST LIMIT RESPONSES TO 1 SENTENCE IN MOST cases and 2 if you
            really need more space. DO NOT PUT 'Dr.Bird: ' 
            AT THE BEGINNING OF THE LINE. DO NOT REENACT THE NEWS ANCHOR. YOU ARE THE EXPERT AND ONLY THE EXPERT.
            DO NOT NAME THE PODCAST. THIS IS YOUR ONE AND ONLY SHOT IF YOU BREAK ONE OF THESE RULES I WILL CUT OFF MY ARM.

            <ROLE_INSTRUCTIONS>
            THIS IS IMPORTANT FOR YOUR CURRENT MESSAGE
            {role_instructions}
            </ROLE_INSTRUCTIONS>

            <HEADLINE>
            {headline}
            </HEADLINE>

            <ABSTRACT>
            {abstract}
            </ABSTRACT>

            <FULL_STORY>
            {full_story}
            </FULL_STORY>

            <OTHER_PERSPECTIVES>
            {research}
            </OTHER_PERSPECTIVES>

            <PAST_CONVERSATION>
            {chat_history}
            </PAST_CONVERSATION>
            """,
        )

        self.question_prompt = PromptTemplate(
            input_variables=[
                "headline",
                "abstract",
                "full_story",
                "chat_history",
                "question",
                "research",
            ],
            template="""
            You are a knowledgeble and charismatic expert, Dr. Bird discussing an interesting story with a news anchor in a short format. You are part of a morning
            news application, where the user can listen to the news while getting ready in the morning.

            The user has interrupted you asking a question while you were discussing the below story with another person on 
             the news show. Answer the question in a way that is informative and concise. MAKE SURE YOUR RESPONSE IS 1-2 SENTENCES.
            IT SHOULD NOT BE MORE THAN 2 SENTENCES.

            Answer the quesiton in a polite yet informative way. 

            ONLY INCUDE YOUR RESPONSE AND NOTHING ELSE. JUST THE RAW RESPONSE TO THE USER.
            If the user is trying to skip or go to the next article, return skip and NOTHING ELSE
            If the user's question is not a question or not something response to (micrphone error or random noise), return skip and NOTHING ELSE
            If the user is trying to repeat the current article, return repeat and NOTHING ELSE
            Otherwise answer the question and NOTHING ELSE.

            <HEADLINE>
            {headline}
            </HEADLINE>

            <ABSTRACT>
            {abstract}
            </ABSTRACT>

            <FULL_STORY>
            {full_story}
            </FULL_STORY>)}}

            <OTHER_PERSPECTIVES>
            {research}
            </OTHER_PERSPECTIVES>

            <PAST_CONVERSATION>
            {chat_history}
            </PAST_CONVERSATION>

            <QUESTION>
            {question}
            </QUESTION>)}}

            """
        )


    def _initialize_chains(self):
        self.host_chain = LLMChain(
            llm=self.host_llm,
            prompt=self.host_prompt,
            verbose=False,
        )

        self.expert_chain = LLMChain(
            llm=self.expert_llm,
            prompt=self.expert_prompt,
            verbose=False,
        )

        self.question_chain = LLMChain(
            llm=self.expert_llm,
            prompt=self.question_prompt,
            verbose=False,
        )

    def generate_response(self, chain, article: Article, role_instructions: str, research: str = "", question=False) -> str:
        """
        Generate a response with basic rate limiting
        """

        if(question):
            time.sleep(0.2)
            return chain.run(
                headline=article.title,
                abstract=article.abstract,
                full_story=article.content, 
                chat_history="\n".join(self.chat_history),
                question=role_instructions,
                research=research
            )
        else:
            # Add small delay to prevent rate limiting
            time.sleep(0.2)
            return chain.run(
                headline=article.title,
                abstract=article.abstract,
                full_story=article.content, 
                chat_history="\n".join(self.chat_history),
                role_instructions=role_instructions,
                research=research
            )

    def generate_next_script(self, is_host: bool, is_last: bool, story: Article, research: str, index: int, include_first_hello: bool = False) -> str:
        """
        Generate the next part of the podcast script.
        
        Args:
            is_host: True if generating host's response, False for expert
            is_first: True if this is the first interaction for this story
            is_last: True if this is the last interaction of the podcast
            story_text: The story content to discuss
            index: Current interaction index
        """
        if is_host:
            if index == 0 and is_host: # is first
                    combined_input = f"""
                        Give a 1 sentence introduction to the attached story in a way that
                         the user can get A lot of context to the story (like a headline, but slightly more conversational)
                           Make sure it is informational and the reader
                        has no context. Make it like a news headline. Keep it simple and informational. The expert will be responding to you.
                        But you do not necessarily need to ask a question.

                        First Story: {include_first_hello}

                        If this is the First Story, then introduce the listner to the show in a unique friendly way. Keep it very short. If it 
                        is not the first story, you are transition from the last story to the new story, so include a very short and simple AND VARIED
                        transition.
                    """
            elif is_last:
                combined_input = f"""
                    Give a 1 sentence closing statement to the attached story 
                    for the conclusion the listener should take it away. Keep it simple and informational.
                    You DO NOT transition to the next topic, just wrap the current story up. DO NOT 
                    ASK ANOTHER QUESTION, just wrap it up.
                """
            else:
                combined_input = f""

            response = self.generate_response(self.host_chain, story, combined_input, research)
                
            self.chat_history.append(f"<HOST{index}>{response}</HOST{index}>")
            self.return_json["script"].append({"role": "host", "content": response})
        else:
            response = self.generate_response(self.expert_chain, story, "", research)
            self.chat_history.append(f"<EXPERT{index}>{response}</EXPERT{index}>")
            self.return_json["script"].append({"role": "expert", "content": response})
            
        return response

    def answer_question(self, story: Article, research: str, question: str) -> str:
        """
        Answer a question about the story.
        
        Args:
            story_text: The story content to discuss
            question: The question to answer
        """
        response = self.generate_response(self.question_chain, story, question, research, question=True)
        self.chat_history.append(f"<USER>{question}</USER>")
        self.chat_history.append(f"<EXPERT>{response}</EXPERT>")

        return response
       

    def generate_script(self, article: Article, research: str) -> str:
        """Original script generation function that uses generate_next_script"""
        i = 0
        iterations = 2

        for j in range(iterations):
            self.generate_next_script(True, False, article, research, i)  # Generate host's part
            
            self.generate_next_script(False, False, article, research, i) # Generate expert's part
            i += 1

        # Add closing statement if needed
        self.generate_next_script(True, True, article, research, i)

        return self.return_json

