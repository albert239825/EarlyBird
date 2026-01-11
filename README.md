# Early Bird: A Dynamic Podcast Generator

Our app is built with **Next.js** and **ShadCN** for the frontend, and **Flask** for the backend. We’ve implemented an agentic workflow that collects current events based on user-selected interests from a vector embedding space, and generates a personalized podcast based on these interests. The podcast generation workflow is fully automated, with each step orchestrated through LangChain.

## Workflow
1. **Event Scraping:**  
   We begin by launching a request to **Perplexity Sonar** to scrape current events based on the user’s chosen interests. The result is a list of headlines that represent the most relevant news stories.

2. **Topic Parsing:**  
   Next, we send these headlines to a **ChatGPT agent** that parses the text and categorizes the stories by topic, allowing us to organize the content effectively.

3. **Deep Research:**  
   The parsed headlines are then sent to another **Perplexity Sonar agent** for a more thorough research dive into each story, gathering additional information and context.

4. **Story Creation:**  
   The results are then sent to a **ChatGPT agent** tasked with synthesizing the information into a coherent podcast outline, setting the stage for the actual script generation.

5. **Podcast Script Generation:**  
   Two specialized **Mistral agents**, an **Expert Agent** and a **Host Agent**, then collaborate to generate the podcast script. These agents interact within the LangChain framework, ensuring a smooth, flowing conversation for the final script.

6. **Text-to-Speech:**  
   Once the script is ready, we send it to **ElevenLabs** for **text-to-speech transcription**, creating a natural-sounding audio file of the podcast.

7. **User Interaction:**  
   The generated audio is presented to the user, who can interrupt at any point to ask follow-up questions. The **Expert Agent** responds in real time, ensuring the conversation remains dynamic and interactive.

8. **3D Embedding Space:**  
   We end with a unique feature—a 3D embedding space where the user can move around to explore their interests, giving them complete control over the type of news content they want to explore in the future.

## Inspiration
Every morning, I start my day by listening to *Up First* by NPR. While I love its concise format, I often found that:
- Some stories didn’t capture my interest.
- At times, the content felt biased.
- I wished I could ask follow-up questions in real time.

These frustrations inspired us to build **Early Bird**—a dynamic podcast generator that not only curates the news you care about but also lets you interact with it.

## What it does
- Curates a personalized podcast based on your unique interests.
- Allows real-time interaction through dynamic interruptions and expert responses.
- Offers an immersive, 3D interface for exploring your interests further.

## How we built it
- **Front End:**  
  - **Next.js** with **ShadCN** for a responsive, modern user interface.
- **Search:**  
  - Integrated **Perplexity Sonar** to fetch up-to-date news based on user interests.
- **Research Distillation:**  
  - Utilized **ChatGPT** to summarize and refine the scraped content.
- **Response Generation:**  
  - Employed **Mistral** for low-latency, dynamic response generation.
- **Backend:**  
  - Built using **Flask** in Python to manage API requests and coordinate the pipeline.
- **Voice Generation:**  
  - Leveraged **11Labs** to convert scripts into natural-sounding audio.
- **Recommender Systems:**  
  - Applied reinforcement learning with **Sherman Morrison optimization** to tailor content recommendations.
- **Data Storage:**  
  - Used **Elastic** and **Intersystems** for vectorized data storage and fast retrieval of podcast episodes.

## Challenges we ran into
- **Building an Interruption System:**  
  - Initially, we generated a single MP3 file for each podcast, which made it difficult to incorporate interactivity. This led to challenges in ensuring real-time responsiveness to user questions and engagement.
- **Pivoting for Reactivity:**  
  - We quickly learned that listeners needed to interact with the content. This realization forced us to reengineer our pipeline to support dynamic interruptions and follow-up responses, ensuring the podcast remains reactive and engaging.

## Accomplishments that we're proud of
- Successfully implementing a fully agentic pipeline with LangChain for the podcast generation process.
- Creating a responsive, immersive experience that gives users control over their podcast content.
- Overcoming technical challenges to build a seamless interruption system for real-time engagement.

## What we learned
- The importance of reactivity in content delivery: Podcasts can be more engaging when listeners have the ability to interact with the content, shaping their experience in real time.
- The power of automation: By using LangChain and various AI agents, we were able to automate complex workflows, reducing manual effort and improving efficiency.
  
## What’s next for Early Bird
- Expanding the personalization options, allowing users to have even more control over the types of content they receive.
- Improving the accuracy and depth of the research agents for even more insightful, data-driven podcast episodes.
- Further enhancing the interactivity of the platform by integrating more dynamic user feedback mechanisms and content curation.
