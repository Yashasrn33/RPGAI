"""
Configuration management for RPGAI backend.
Loads settings from environment variables with .env support.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"
    
    # Google Cloud TTS
    google_application_credentials: str = ""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    # Database
    db_path: str = "npc_memory.db"
    
    # Media
    media_dir: str = "./media"
    media_base_url: str = "http://localhost:8000/media"
    
    # Model parameters
    temperature: float = 0.7
    top_p: float = 0.9
    max_output_tokens: int = 220
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Validate critical settings
if not settings.gemini_api_key:
    print("⚠️  WARNING: GEMINI_API_KEY not set. Please configure .env file.")

if not settings.google_application_credentials:
    print("⚠️  WARNING: GOOGLE_APPLICATION_CREDENTIALS not set. TTS will not work.")
else:
    # Set environment variable for Google Cloud SDK
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials

# Ensure media directory exists
Path(settings.media_dir).mkdir(parents=True, exist_ok=True)

