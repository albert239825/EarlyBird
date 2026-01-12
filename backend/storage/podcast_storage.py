"""
Storage utilities for saving podcasts and metadata.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class PodcastStorage:
    """Handles saving and managing podcast files and metadata"""
    
    def __init__(self, backend_root: Path):
        """
        Initialize podcast storage.
        
        Args:
            backend_root: Root directory of the backend
        """
        self.backend_root = backend_root
        self.finished_podcasts_dir = backend_root / "finished_podcasts"
        self.metadata_file = self.finished_podcasts_dir / "podcast_metadata.json"
        
        # Ensure directories exist
        self.finished_podcasts_dir.mkdir(parents=True, exist_ok=True)
    
    def save_transcript(self, transcript: str, podcast_dir: Path) -> Path:
        """
        Save podcast transcript to file.
        
        Args:
            transcript: Transcript content
            podcast_dir: Directory where podcast files are stored
            
        Returns:
            Path to the saved transcript file
        """
        transcript_path = podcast_dir / "transcript.txt"
        transcript_path.write_text(transcript, encoding='utf-8')
        logger.info(f"Transcript saved to: {transcript_path}")
        return transcript_path
    
    def save_manifest(self, podcast_dir: Path, manifest: Dict[str, Any]) -> Path:
        """
        Save manifest.json to podcast directory.
        
        Args:
            podcast_dir: Directory where podcast files are stored
            manifest: Manifest dictionary
            
        Returns:
            Path to the saved manifest file
        """
        path = podcast_dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Manifest saved to: {path}")
        return path
    
    def load_manifest(self, podcast_dir: Path) -> Dict[str, Any]:
        """
        Load manifest.json from podcast directory.
        
        Args:
            podcast_dir: Directory where podcast files are stored
            
        Returns:
            Manifest dictionary
        """
        path = podcast_dir / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    
    def get_podcast_dir(self, podcast_id: str) -> Path:
        """
        Get podcast directory by ID.
        
        Args:
            podcast_id: Podcast directory name
            
        Returns:
            Path to podcast directory
        """
        return self.finished_podcasts_dir / podcast_id
    
    def save_metadata(self, podcast_dir: Path, additional_data: Optional[Dict[str, Any]] = None):
        """
        Save podcast metadata to the central metadata file.
        
        Args:
            podcast_dir: Directory where podcast files are stored
            additional_data: Optional additional metadata to save
        """
        # Initialize metadata file if it doesn't exist
        if not self.metadata_file.exists():
            self.metadata_file.write_text(json.dumps({"metadata": []}, indent=4))
        
        # Read existing metadata
        with open(self.metadata_file, "r") as f:
            data = json.load(f)
        
        # Add new entry
        entry = {
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "podcast_dir": str(podcast_dir),
        }
        
        if additional_data:
            entry.update(additional_data)
        
        data["metadata"].append(entry)
        
        # Save updated metadata
        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=4)
        
        logger.info(f"Metadata saved for podcast: {podcast_dir}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Retrieve all podcast metadata.
        
        Returns:
            Dictionary containing all metadata
        """
        if not self.metadata_file.exists():
            return {"metadata": []}
        
        with open(self.metadata_file, "r") as f:
            return json.load(f)
    
    def find_podcast_by_filepath(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Find podcast metadata by file path.
        
        Args:
            filepath: Path to search for
            
        Returns:
            Podcast metadata if found, None otherwise
        """
        metadata = self.get_metadata()
        for entry in metadata.get("metadata", []):
            if "file_path" in entry and filepath in entry["file_path"]:
                return entry
        return None
