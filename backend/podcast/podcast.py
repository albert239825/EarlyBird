import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

print(os.getcwd())
from backend.podcast.agents.audio.audio_generation import PodcastAudioGenerator
from backend.podcast.agents.pipeline import NewsPodcastPipeline

from backend.podcast.AppData import AppData
from backend.podcast.agents.audio.audio_generation import PodcastAudioGenerator
from backend.podcast.agents.pipeline import NewsPodcastPipeline

print(os.getcwd())
from backend.podcast.agents.audio.audio_generation import PodcastAudioGenerator
from backend.podcast.agents.pipeline import NewsPodcastPipeline

import json

load_dotenv()  # Load environment variables from .env file

import logging

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# openai turn off logging
logging.getLogger("openai").setLevel(logging.WARNING)

# httpcore turn off logging
logging.getLogger("httpcore").setLevel(logging.WARNING)

# hide pydub
logging.getLogger("pydub").setLevel(logging.WARNING)

class PodcastRunner:
    def __init__(self):
        # Get the absolute path to the project root
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Create a unique directory for this podcast
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        podcast_id = str(uuid.uuid4())[:8]
        self.podcast_dir = os.path.join(
            self.project_root,
            'backend',
            'podcast', 
            'finished_podcasts',
            f'podcast_{timestamp}_{podcast_id}'
        )
        # Create the directory if it doesn't exist
        os.makedirs(self.podcast_dir, exist_ok=True)
        
        self.pipeline = NewsPodcastPipeline(
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            mistral_api_key=os.getenv("MISTRAL_API_KEY")
        )
        # Pass the output directory to PodcastAudioGenerator
        self.audio_generator = PodcastAudioGenerator(output_dir=self.podcast_dir)

    def save_transcript(self, script: str, filepath: str):
        """Save the transcript to a file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(script)

    def run(self):
        # Generate the script
        script = self.pipeline.generate_podcast()
        print("Script generated, saving transcript...")
        
        # Save the transcript
        transcript_path = os.path.join(self.podcast_dir, 'transcript.txt')
        self.save_transcript(script, transcript_path)
        print(f"Transcript saved to: {transcript_path}")
        
        # Generate the audio
        # print("Generating audio...")
        # audio_path = self.audio_generator.generate_audio(script)
        # print(f"Podcast saved to: {audio_path}")

        json_file_path = os.path.join(
            self.project_root,
            'backend',
            'podcast',
            'finished_podcasts',
            'podcast_metadata.json'
        )
        
        # Create metadata file if it doesn't exist
        if not os.path.exists(json_file_path):
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
            with open(json_file_path, "w") as file:
                json.dump({"metadata": []}, file)

        # Read existing data
        with open(json_file_path, "r") as file:
            data = json.load(file)

        data["metadata"].append({
            # "file_path": audio_path, 
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stories": self.pipeline.stories
        })

        with open(json_file_path, "w") as file:
            json.dump(data, file, indent=4)
        
        return {
            'transcript_path': transcript_path,
            # 'audio_path': audio_path,
            'podcast_dir': self.podcast_dir
        }
    
    def run_next(self, index: int):
        script = self.pipeline.generate_next_part_podcast(index)
        print("Script generated, saving transcript...")
    
    def answer_question(self, index: int, question: str):
        answer = self.pipeline.answer_question(question, index)
        print("Answer generated")
        return answer

    def generate_from_transcript(self, transcript_path: str):
        """Generate audio from an existing transcript file."""
        # Create a unique directory for this test podcast
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        podcast_id = str(uuid.uuid4())[:8]
        self.podcast_dir = os.path.join(
            self.project_root, 
            'podcast', 
            'agents', 
            'audio', 
            'finished_podcasts',
            f'test_podcast_{timestamp}_{podcast_id}'
        )
        os.makedirs(self.podcast_dir, exist_ok=True)

        # Read the transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            script = f.read()

        # Generate the audio
        print("Generating audio from transcript...")
        audio_path = self.audio_generator.generate_audio(script)
        print(f"Test podcast saved to: {audio_path}")
        
        return {
            'transcript_path': transcript_path,
            'audio_path': audio_path,
            'podcast_dir': self.podcast_dir
        }
    


if __name__ == "__main__":
    import sys
    runner = PodcastRunner()
    
    if len(sys.argv) > 1:
        transcript_path = sys.argv[1]
        if not os.path.exists(transcript_path):
            print(f"Error: Transcript file not found: {transcript_path}")
            sys.exit(1)
        result = runner.generate_from_transcript(transcript_path)
        print(f"\nPodcast generation from transcript complete!")
        print(f"Output directory: {result['podcast_dir']}")
        print(f"Original transcript: {result['transcript_path']}")
        print(f"Generated audio: {result['audio_path']}")
    else:
        result = runner.run()
        print(f"\nPodcast generation complete!")
        print(f"Output directory: {result['podcast_dir']}")
        print(f"Transcript: {result['transcript_path']}")
        print(f"Audio: {result['audio_path']}")

