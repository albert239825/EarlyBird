"""
Centralized configuration for the EarlyBird backend.
All environment variables and configuration settings are defined here.
"""
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent
    BACKEND_ROOT = Path(__file__).parent
    PODCAST_DIR = BACKEND_ROOT / "finished_podcasts"
    
    # API Keys
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    NYT_API_KEY = os.getenv("NYT_API_KEY")
    
    # Flask Configuration
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 8000))
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    
    # CORS
    CORS_ALLOWED_ORIGINS = "*"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Audio Generation
    GENERATE_AUDIO = os.getenv("GENERATE_AUDIO", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate that required environment variables are set"""
        required_keys = [
            "PERPLEXITY_API_KEY",
            "OPENAI_API_KEY",
            "MISTRAL_API_KEY",
        ]
        # ELEVENLABS_API_KEY only required if audio generation is enabled
        if cls.GENERATE_AUDIO:
            required_keys.append("ELEVENLABS_API_KEY")
        
        missing = [key for key in required_keys if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        cls.PODCAST_DIR.mkdir(parents=True, exist_ok=True)
