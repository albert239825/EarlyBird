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
from typing import List, Optional, Dict, Any

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

    def generate_script_assets(
        self,
        podcast_dir: Path,
        num_articles: int = 2,
        categories: Optional[List[Optional[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Phase 1 only: Generate research docs + HQ script utterances (no audio).
        
        Args:
            podcast_dir: Directory for podcast files
            num_articles: Number of articles/stories
            categories: Optional list of categories per story
            
        Returns:
            Dictionary with podcast_id and stories metadata
        """
        logger.info(f"Generating script assets for: {podcast_dir.name}")
        
        podcast_json = self.pipeline.generate_research_and_script_assets(
            podcast_dir=podcast_dir,
            num_articles=num_articles,
            categories=categories,
        )
        
        # Save metadata
        self.storage.save_metadata(podcast_dir, additional_data={"podcast_id": podcast_dir.name})
        logger.info(f"Script generation complete: {podcast_dir} ({len(podcast_json.get('stories', []))} stories)")
        
        return podcast_json
    
    def generate_audio_assets(self, podcast_dir: Path) -> Dict[str, Any]:
        """
        Phase 2 only: Generate audio segments + manifest from existing scripts.
        
        Args:
            podcast_dir: Directory containing script files
            
        Returns:
            Manifest dictionary
        """
        logger.info(f"Generating audio assets for: {podcast_dir.name}")
        
        if not podcast_dir.exists():
            raise FileNotFoundError(f"Podcast directory not found: {podcast_dir}")
        
        # Check if script files exist
        script_dir = podcast_dir / "script"
        if not script_dir.exists():
            raise ValueError(f"No script directory found in {podcast_dir}. Run script generation first.")
        
        script_files = list(script_dir.glob("story_*.json"))
        if not script_files and not (script_dir / "intro.json").exists():
            raise ValueError(f"No script files found in {script_dir}. Run script generation first.")
        
        audio_generator = PodcastAudioGenerator(output_dir=str(podcast_dir / "audio"))
        manifest = self.pipeline.generate_audio_segments_and_manifest(
            podcast_dir=podcast_dir,
            audio_generator=audio_generator
        )
        
        # Save manifest
        self.storage.save_manifest(podcast_dir, manifest)
        logger.info(f"Audio generation complete: {podcast_dir} ({len(manifest.get('segments', []))} segments)")
        
        return manifest

    def generate_podcast(
        self,
        podcast_dir: Path,
        num_articles: int = 2,
        categories: Optional[List[Optional[str]]] = None,
    ):
        """
        Phase 1 + 2: research docs + HQ script utterances + pregen audio segments + manifest.
        """
        logger.info(f"Starting full podcast generation for: {podcast_dir.name}")

        # Phase 1: Research + Script
        podcast_json = self.generate_script_assets(
            podcast_dir=podcast_dir,
            num_articles=num_articles,
            categories=categories,
        )

        # Phase 2: Audio segments + Manifest (only if GENERATE_AUDIO is enabled)
        if Config.GENERATE_AUDIO:
            manifest = self.generate_audio_assets(podcast_dir)
            logger.info(f"Podcast generation complete: {podcast_dir} ({len(podcast_json.get('stories', []))} stories, {len(manifest.get('segments', []))} segments)")
        else:
            logger.info("Audio generation disabled (GENERATE_AUDIO=false) - skipping Phase 2")

        return podcast_json
    
    def get_podcast_dir_by_id(self, podcast_id: str) -> Path:
        """
        Get podcast directory by ID.
        
        Args:
            podcast_id: Podcast ID (directory name)
            
        Returns:
            Path to podcast directory
            
        Raises:
            FileNotFoundError: If podcast directory doesn't exist
        """
        podcast_dir = self.storage.get_podcast_dir(podcast_id)
        if not podcast_dir.exists():
            raise FileNotFoundError(f"Podcast not found: {podcast_id}")
        return podcast_dir
    
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
