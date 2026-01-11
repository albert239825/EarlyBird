from agents.interest_classifier import InterestClassifierAgent
from agents.scraper import NewsScraperAgent
from agents.researcher import DeepResearchAgent
from agents.story_drafter import StoryDrafterAgent
from agents.script_generator import PodcastScriptGenerator
from langchain.prompts import PromptTemplate
import re

import os
import re
from dotenv import load_dotenv
load_dotenv()

perplexity_api_key=os.getenv("PERPLEXITY_API_KEY")
openai_api_key=os.getenv("OPENAI_API_KEY")
mistral_api_key=os.getenv("MISTRAL_API_KEY")
test_component = 'script_generator'

# Interest Classifier
if test_component == 'interest_classifier':
    interest_classifier_prompt = PromptTemplate(
                input_variables=["user_interests"],
                template="""
                Here is a list of user interests: {user_interests}
                Generate a list of 3 broad categories based on the user's interests. These categories should be distinct and relatively unrelated from each other and heavily relate to the user's categories given:
                
                The topics should be outputted as <TOPIC> topic 1 </TOPIC> <TOPIC> topic 2 </TOPIC> <TOPIC> topic 3 </TOPIC>
                INCLUDE THE <TOPIC> TAGS
                """
            )

    user_interests_test_cases = [
    ["Urban Planning", "Beekeeping", "Astrobiology", "Minimalist Living", "Cryptography", "Sumo Wrestling", "Mushroom Foraging", "Antique Restoration"],
    ["Taxidermy", "Historical Conspiracy Theories", "Competitive Eating", "Numismatics (Coin Collecting)", "Renaissance Music", "Desert Survival Skills", "Parapsychology", "Knot Tying"],
    ["Guerilla Gardening", "Traditional Archery", "Sanskrit Studies", "Synesthesia Research", "Urban Legends", "Maritime Navigation", "Sculpting with Ice", "Quantum Computing"],
    ["Whale Watching", "Experimental Theater", "Trainspotting", "Ethical Hacking", "Genealogy", "Steampunk Fashion", "Morse Code Communication", "Silent Film Appreciation"],
    ["Ancient Siege Warfare", "Subterranean Exploration (Caving)", "Kintsugi (Japanese Art of Repairing Pottery)", "Meteorology", "Tuvan Throat Singing", "Alchemical Studies", "Propaganda Analysis", "Competitive Yo-Yoing"]
]

    interest_classifier = InterestClassifierAgent(openai_api_key, interest_classifier_prompt)
    for i in user_interests_test_cases:
        interests = interest_classifier.interest_classify(i)
        print(str(i) + ': ' + interests)

# Scraper
if test_component == 'scraper':
    categories = [
        "<TOPIC> Urban Planning </TOPIC><TOPIC> Beekeeping </TOPIC><TOPIC> Cryptography </TOPIC>",
        "<TOPIC> Taxidermy </TOPIC><TOPIC> Numismatics </TOPIC><TOPIC> Competitive Eating </TOPIC>",
    ]
    seperated_categories = [re.findall(r'<TOPIC>\s*(.*?)\s*</TOPIC>', s) for s in categories]
    print(seperated_categories)
    for i in seperated_categories:
        for j in i:
            scraper = NewsScraperAgent(perplexity_api_key)
            headlines = scraper.get_top_headlines(j)
            print(j + ': ' + headlines['content'])

# Researcher
if test_component == 'researcher':
    headlines = ["City of Brotherly Love Soars: Philadelphia Honors Eagles After Super Bowl LIX Win", 
    "Justice Served: Arrest made in brutal stabbing of beloved Cherry Hill veterinarian", 
    "Breaking News: Russian Drone Breaches Chernobyl Nuclear Plant\'s Shield", 
    "Breaking News: 3 Hostages Freed from Gaza Captivity - A Miraculous Escape!", 
    "Breaking News: UN Urges Immediate Ceasefire in Gaza to Prevent Humanitarian Crisis"
    ]
    for i in headlines:
        researcher = DeepResearchAgent(perplexity_api_key)
        researched_stories = researcher.research_stories(i)
        print(i + ': ' + str(researched_stories[0]["research"]['choices'][0]["message"]["content"]))

# Story Drafter
if test_component == 'story_drafter':
    story_drafter_prompt = PromptTemplate(
            input_variables=["story_data"],
            template="""
            Draft a compelling podcast story based on this research:
            {story_data}
            Include a hook to grab attention, a clear narrative structure, key points and analysis, engaging transitions, and thought-provoking conclusions.
            Ensure all the facts and evidence related to the story from the research are incorporated in a coherent and engaging manner and remain in the story.
            ONLY OUTPUT THE STORY PRODUCED BASED ON THE RESEARCH. DO NOT RETURN ANY OTHER TEXT.
            """
        )

    researched_stories = ["""
        City of Brotherly Love Soars: Philadelphia Honors Eagles After Super Bowl LIX Win: ## Overview of the Event

    The Philadelphia Eagles won Super Bowl LIX by defeating the Kansas City Chiefs 40-22, marking their second Super Bowl victory. This win was celebrated with a grand parade in Philadelphia, where fans and players alike rejoiced in the team's triumph.

    ## Expert Opinions

    - **Coach Nick Sirianni**: Highlighted the team's collective effort, stating, "This is the ultimate team game. You can't be great without the greatness of others. Great performance by everybody — offense, defense, special teams" [5].
    - **Jalen Hurts**: Emphasized the role of defense in their victory, saying, "Defense wins championships. We saw how they played today. We saw the difference they made in the game" [5].

    ## Related Events

    - **Parade Celebration**: The city of Philadelphia held a victory parade on Valentine's Day, where thousands of fans gathered to celebrate the Eagles' win. The parade route stretched from South Philadelphia to the Philadelphia Museum of Art, with fans camping out overnight to secure prime spots [2][4].
    - **Player Interactions**: Players like Saquon Barkley and Cooper DeJean interacted with fans, exchanging high-fives and taking photos. A.J. Brown addressed criticism he faced during the season, proclaiming, "You gonna get all those things wrong about me, but one thing you get right: I'm a f---ing champion!" [2].

    ## Statistical Data

    - **Game Statistics**: The Eagles dominated the game, shutting out the Chiefs in the first half. Jalen Hurts threw for 221 yards and two touchdowns, while also rushing for a score. The Eagles' defense sacked Patrick Mahomes six times, including 2.5 by Josh Sweat [5].
    - **Turnovers**: The Eagles' defense forced three turnovers, including a pick-six by Cooper DeJean on his 22nd birthday [5].     

    ## Future Implications

    - **Team Dynamics**: The victory solidifies the Eagles as a formidable team in the NFL, with a strong defense and offense. This win could set the stage for future success, especially with key players like Jalen Hurts and Saquon Barkley [1][5].
    - **Fan Engagement**: The celebration and parade highlight the strong bond between the team and its fans, which could contribute to sustained fan support and enthusiasm in upcoming seasons [2][4].
    """,
    """
    Justice Served: Arrest made in brutal stabbing of beloved Cherry Hill veterinarian: ## Overview of the Case

    - **Arrest and Charges**: Cristian Custodio-Aquino, a 27-year-old man from Portland, Oregon, was arrested and charged with first-degree murder in connection with the stabbing death of Dr. Michael Anthony, a veterinarian in Cherry Hill, New Jersey. The arrest was made by U.S. Marshals in Fresno, California, on February 11, 2025[1][2].

    - **Victim Profile**: Dr. Michael Anthony, 45, was a well-respected veterinarian who owned Haddon Vet in Haddon Heights and worked at various general and emergency practices in Camden, Gloucester, and Ocean counties. He was found unconscious with multiple stab wounds in front of his home on Sharrowvalle Road in Cherry Hill on December 10, 2024[2].

    ## Investigation Details

    - **Investigation Process**: The Camden County Prosecutor’s Office Homicide Unit and Cherry Hill Police Department conducted a comprehensive investigation. They identified Custodio-Aquino as the suspect after analyzing evidence, including a pair of prescription glasses found near the crime scene that were sold to him in Washington State[1][2].

    - **Security Footage**: A black sedan was captured on security footage leaving the neighborhood around the time of the murder. The vehicle was later tracked to Pennsylvania, Florida, Alabama, and Texas. It had been in New Jersey since October and was in the Haddon Township area until December 8[2].

    ## Expert Opinions and Community Reaction

    - **Community Response**: Cherry Hill Mayor Dave Fleisher expressed relief that a suspect was apprehended, noting the community's ongoing mourning for Dr. Anthony[2].

    - **Lack of Motive Disclosure**: Prosecutors have not disclosed a motive for the murder. The complaint and affidavit indicate that Anthony and Custodio-Aquino were acquaintances, but further details were not provided[2].

    ## Statistical Data and Future Implications

    - **Crime Statistics**: This case highlights the rarity of such violent crimes in Cherry Hill, a generally safe community. The arrest and charges may provide some reassurance to residents.

    - **Future Implications**: The case's resolution could impact community trust in law enforcement and may influence future investigations into similar crimes. The extradition process for Custodio-Aquino is ongoing, with potential legal proceedings to follow in New Jersey[1][2].

    ## Evidence and Facts

    - **Physical Evidence**: The prescription glasses found at the crime scene were a crucial piece of evidence linking Custodio-Aquino to the crime[2].

    - **Extradition Status**: Custodio-Aquino is currently being held at the Fresno County Jail awaiting extradition to New Jersey[1][2].
    """
    ]

    for i in researched_stories:
        story_drafter = StoryDrafterAgent(openai_api_key, story_drafter_prompt)
        story = story_drafter.draft_stories(i)
        print(story)

# Script Generator
if test_component == 'script_generator':
    drafted_stories = [{"topic" : "Sports", "story": """In the bustling city of Philadelphia, the spirit of brotherly love soared to new heights as the Philadelphia Eagles clinched victory in Super Bowl LIX, defeating the Kansas City Chiefs with a resounding score of 40-22. This triumph marked the Eagles' second Super Bowl win, igniting a wave of jubilation among fans and players alike.\n\nCoach Nick Sirianni lauded the team's collective effort, emphasizing the essence of teamwork in achieving greatness. Jalen Hurts echoed this sentiment, attributing their success to the stellar performance of the defense, underscoring the age-old adage that defense wins championships.\n\nThe streets of Philadelphia came alive with fervor as the city hosted a grand parade on Valentine's Day to honor the victorious Eagles. Thousands of fans flocked to the parade route, camping out overnight to secure prime viewing spots from South Philadelphia to the iconic Philadelphia Museum of Art. The celebration was not just limited to the players on the field; players like Saquon Barkley and Cooper DeJean engaged with fans, sharing in the joy and excitement of the moment.\n\nStatistically, the Eagles' dominance in the game was evident, with Jalen Hurts showcasing his prowess by throwing for 221 yards and two touchdowns, in addition to a rushing score. The defense, led by standout performances from players like Josh Sweat and Cooper DeJean, made a significant impact by sacking Patrick Mahomes six times and forcing three crucial turnovers.\n\nLooking ahead, the Eagles' victory solidifies their status as a force to be reckoned with in the NFL, setting the stage for future success with key players like Jalen Hurts and Saquon Barkley leading the charge. The strong bond between the team and its passionate fan base, exemplified by the exuberant parade celebrations, bodes well for sustained fan engagement and unwavering support in the seasons to come.\n\nIn the heart of Philadelphia, a tale of triumph and unity unfolded, showcasing the power of teamwork, resilience, and unwavering dedication. As the Eagles soar to new heights, their victory in Super Bowl LIX will forever be etched in the annals of football history, a testament to the unbreakable bond between a team, its fans, and a city united in the pursuit of greatness."""},
                       {"topic" : "Crime", "story": """In a quiet and close-knit community like Cherry Hill, New Jersey, the brutal stabbing of beloved veterinarian Dr. Michael Anthony sent shockwaves through the town. The arrest of 27-year-old Cristian Custodio-Aquino in connection with the murder brought a sense of relief but also raised questions about the motive behind such a heinous crime.\n\nDr. Anthony, known for his dedication to caring for animals, was found with multiple stab wounds in front of his home, leaving residents in mourning. The investigation, led by the Camden County Prosecutor’s Office Homicide Unit and Cherry Hill Police Department, uncovered crucial evidence linking Custodio-Aquino to the crime, including a pair of prescription glasses sold to him in Washington State.\n\nSecurity footage capturing a black sedan leaving the neighborhood around the time of the murder led authorities on a multi-state chase before apprehending the suspect in Fresno, California. The lack of a disclosed motive left the community puzzled, but the arrest and charges provided some reassurance in a community not accustomed to such violent crimes.\n\nAs Custodio-Aquino awaits extradition to New Jersey, the community grapples with the implications of this tragic event. The resolution of the case could impact trust in law enforcement and future investigations into similar crimes, shedding light on the rare occurrence of such violence in Cherry Hill.\n\nWith physical evidence and facts pointing to Custodio-Aquino's involvement, the case serves as a reminder of the fragility of safety in even the most peaceful communities. As the legal proceedings unfold, the story of Dr. Anthony's untimely death serves as a cautionary tale and a call for justice to be served in the face of senseless violence."""},
                    #    {"topic" : ""}
                     ]
    script_generator = PodcastScriptGenerator(mistral_api_key)
    script = script_generator.generate_script(drafted_stories)
    print(script)
