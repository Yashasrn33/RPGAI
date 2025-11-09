"""
Google Cloud Speech-to-Text integration.
Transcribes player audio input to text for dialogue processing.
"""
import logging
from typing import Optional
from google.cloud import speech_v1
from google.cloud.speech_v1 import types

from .settings import settings

logger = logging.getLogger(__name__)


class STTClient:
    """
    Google Cloud Speech-to-Text client.
    Transcribes audio files to text for player input.
    """
    
    def __init__(self):
        """Initialize the STT client."""
        try:
            self.client = speech_v1.SpeechClient()
            logger.info("STTClient initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize STT client: {e}")
            self.client = None
    
    def transcribe(
        self,
        audio_content: bytes,
        language_code: str = "en-US",
        sample_rate_hertz: int = 16000,
        encoding: speech_v1.RecognitionConfig.AudioEncoding = speech_v1.RecognitionConfig.AudioEncoding.LINEAR16
    ) -> Optional[str]:
        """
        Transcribe audio content to text.
        
        Args:
            audio_content: Raw audio bytes
            language_code: Language code (default: en-US)
            sample_rate_hertz: Audio sample rate (default: 16000)
            encoding: Audio encoding format
        
        Returns:
            Transcribed text, or None if transcription failed
        """
        if not self.client:
            logger.error("STT client not initialized")
            return None
        
        try:
            # Configure audio
            audio = types.RecognitionAudio(content=audio_content)
            
            # Configure recognition
            config = types.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=sample_rate_hertz,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="default",  # Use "latest_long" for better quality on longer audio
            )
            
            # Perform synchronous recognition
            response = self.client.recognize(config=config, audio=audio)
            
            if not response.results:
                logger.warning("No transcription results returned")
                return None
            
            # Get the best transcription
            transcription = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            logger.info(f"Transcribed: '{transcription}' (confidence: {confidence:.2f})")
            return transcription.strip()
            
        except Exception as e:
            logger.error(f"STT transcription failed: {e}", exc_info=True)
            return None
    
    def transcribe_from_file_format(
        self,
        audio_content: bytes,
        file_format: str = "wav",
        language_code: str = "en-US"
    ) -> Optional[str]:
        """
        Transcribe audio with automatic format detection.
        
        Args:
            audio_content: Raw audio bytes
            file_format: File format (wav, mp3, flac, ogg, webm)
            language_code: Language code
        
        Returns:
            Transcribed text, or None if failed
        """
        # Map file format to GCP encoding
        encoding_map = {
            "wav": speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            "mp3": speech_v1.RecognitionConfig.AudioEncoding.MP3,
            "flac": speech_v1.RecognitionConfig.AudioEncoding.FLAC,
            "ogg": speech_v1.RecognitionConfig.AudioEncoding.OGG_OPUS,
            "webm": speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        }
        
        encoding = encoding_map.get(file_format.lower(), speech_v1.RecognitionConfig.AudioEncoding.LINEAR16)
        
        if not self.client:
            logger.error("STT client not initialized")
            return None
        
        try:
            # Configure audio
            audio = types.RecognitionAudio(content=audio_content)
            
            # Configure recognition - GCP can auto-detect sample rate from WAV headers
            # For compressed formats (MP3, FLAC, etc.), sample rate is also auto-detected
            config_args = {
                "encoding": encoding,
                "language_code": language_code,
                "enable_automatic_punctuation": True,
                "model": "default",
            }
            
            # Don't set sample_rate_hertz - let GCP auto-detect from file header
            # This works for both WAV (reads from header) and compressed formats
            
            config = types.RecognitionConfig(**config_args)
            
            # Perform synchronous recognition
            response = self.client.recognize(config=config, audio=audio)
            
            if not response.results:
                logger.warning("No transcription results returned")
                return None
            
            # Get the best transcription
            transcription = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            logger.info(f"Transcribed: '{transcription}' (confidence: {confidence:.2f})")
            return transcription.strip()
            
        except Exception as e:
            logger.error(f"STT transcription failed: {e}", exc_info=True)
            return None


# Global STT client instance
stt_client = STTClient()


def transcribe_audio(
    audio_content: bytes,
    file_format: str = "wav",
    language_code: str = "en-US"
) -> Optional[str]:
    """
    Convenience function for transcribing audio.
    This is what the FastAPI endpoint calls.
    
    Args:
        audio_content: Raw audio bytes
        file_format: Audio file format (wav, mp3, flac, ogg, webm)
        language_code: Language code (default: en-US)
    
    Returns:
        Transcribed text, or None if failed
    """
    return stt_client.transcribe_from_file_format(audio_content, file_format, language_code)

