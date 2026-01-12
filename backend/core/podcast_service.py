"""
Podcast service - main business logic for podcast generation.
"""
from pathlib import Path
from backend.core.pipeline import PodcastPipeline
from backend.audio.generator import PodcastAudioGenerator
from backend.storage.podcast_storage import PodcastStorage
from backend.storage.paths import generate_podcast_dir
from backend.core.state_manager import PodcastState
from backend.config import Config
from backend.utils.logging_config import get_logger
from typing import List, Optional

logger = get_logger(__name__)


class PodcastService:
    """
    Main service for podcast generation.
    Coordinates the pipeline, storage, and audio generation.
    """
    
    def __init__(self, state: PodcastState = None):
        """
        Initialize the podcast service.
        
        Args:
            state: Optional PodcastState instance. If not provided, creates a new one.
        """
        self.state = state if state else PodcastState()
        self.backend_root = Config.BACKEND_ROOT

        # Initialize components (create per-run podcast dirs later)
        self.pipeline = PodcastPipeline(
            perplexity_api_key=Config.PERPLEXITY_API_KEY,
            openai_api_key=Config.OPENAI_API_KEY,
            mistral_api_key=Config.MISTRAL_API_KEY,
            state=self.state
        )
        self.storage = PodcastStorage(self.backend_root)

    def create_podcast_dir(self) -> Path:
        """Create a unique podcast directory and return it."""
        return generate_podcast_dir(Config.PODCAST_DIR)

    def generate_podcast(
        self,
        podcast_dir: Path,
        num_articles: int = 2,
        categories: Optional[List[Optional[str]]] = None,
    ):
        """
        Phase 1 + 2: research docs + HQ script utterances + pregen audio segments + manifest.
        """
        logger.info(f"Starting podcast generation for: {podcast_dir.name}")

        # Phase 1: Research + Script
        podcast_json = self.pipeline.generate_research_and_script_assets(
            podcast_dir=podcast_dir,
            num_articles=num_articles,
            categories=categories,
        )

        # Phase 2: Audio segments + Manifest
        audio_generator = PodcastAudioGenerator(output_dir=str(podcast_dir / "audio"))
        manifest = self.pipeline.generate_audio_segments_and_manifest(
            podcast_dir=podcast_dir,
            audio_generator=audio_generator
        )
        
        # Save manifest
        self.storage.save_manifest(podcast_dir, manifest)

        # Save metadata centrally (minimally, just point at the directory)
        self.storage.save_metadata(podcast_dir, additional_data={"podcast_id": podcast_dir.name})
        logger.info(f"Podcast generation complete: {podcast_dir} ({len(podcast_json.get('stories', []))} stories, {len(manifest.get('segments', []))} segments)")

        return podcast_json
    
    def generate_next_part(self, index: int):
        """
        Generate the next part of a podcast script.
        
        Args:
            index: Article index
        """
        logger.info(f"Generating next part for article {index}...")
        script = self.pipeline.generate_next_part_podcast(index)
        logger.info("Script part generated")
        return script
    
    def answer_question(self, index: int, question: str):
        """
        Answer a user question about an article.
        
        Args:
            index: Article index
            question: User's question
            
        Returns:
            Answer text
        """
        logger.info(f"Answering question for article {index}: {question}")
        answer = self.pipeline.answer_question(question, index)
        logger.info("Answer generated")
        return answer
    
    def generate_from_transcript(self, transcript_path: str):
        """
        Generate audio from an existing transcript file.
        
        Args:
            transcript_path: Path to the transcript file
            
        Returns:
            Dictionary with paths to generated files
        """
        transcript_path = Path(transcript_path)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
        
        # Create a unique directory for this test podcast
        podcast_dir = generate_podcast_dir(Config.PODCAST_DIR)
        podcast_dir = podcast_dir.parent / f"test_{podcast_dir.name}"
        podcast_dir.mkdir(parents=True, exist_ok=True)

        # Read the transcript
        script = transcript_path.read_text(encoding='utf-8')

        # Generate the audio
        logger.info("Generating audio from transcript...")
        audio_generator = PodcastAudioGenerator(output_dir=str(podcast_dir))
        audio_path = audio_generator.generate_audio(script)
        logger.info(f"Test podcast saved to: {audio_path}")
        
        return {
            'transcript_path': str(transcript_path),
            'audio_path': audio_path,
            'podcast_dir': str(podcast_dir)
        }
