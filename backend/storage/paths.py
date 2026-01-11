"""
Path utilities for file storage.
"""
from pathlib import Path
from datetime import datetime
import uuid


def generate_podcast_dir(base_dir: Path) -> Path:
    """
    Generate a unique directory name for a podcast.
    
    Args:
        base_dir: Base directory where podcasts are stored
        
    Returns:
        Path to the new podcast directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    podcast_id = str(uuid.uuid4())[:8]
    podcast_dir = base_dir / f"podcast_{timestamp}_{podcast_id}"
    podcast_dir.mkdir(parents=True, exist_ok=True)
    return podcast_dir


def get_finished_podcasts_dir(backend_root: Path) -> Path:
    """Get the finished podcasts directory"""
    return backend_root / "finished_podcasts"


def get_metadata_file_path(backend_root: Path) -> Path:
    """Get the path to the podcast metadata JSON file"""
    return get_finished_podcasts_dir(backend_root) / "podcast_metadata.json"
