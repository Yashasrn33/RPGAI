"""
Google Cloud Text-to-Speech integration with SSML support.
Converts NPC utterances to audio files for Unity playback.
"""
import uuid
import logging
from pathlib import Path
from typing import Optional
from google.cloud import texttospeech

from schemas import Emotion, SSMLStyle
from settings import settings

logger = logging.getLogger(__name__)


class TTSClient:
    """
    Google Cloud TTS client with SSML formatting.
    Generates audio files from NPC dialogue and returns URLs.
    """
    
    def __init__(self):
        """Initialize the TTS client."""
        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("TTSClient initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize TTS client: {e}")
            self.client = None
    
    def build_ssml(
        self,
        text: str,
        emotion: Optional[Emotion] = None,
        style: Optional[SSMLStyle] = None
    ) -> str:
        """
        Wrap text in SSML with emotional prosody adjustments.
        
        Args:
            text: The utterance text
            emotion: Emotional state for prosody tuning
            style: SSML style override
        
        Returns:
            SSML-formatted string
        """
        # Base prosody settings
        rate = "100%"
        pitch = "+0st"
        volume = "medium"
        
        # Adjust based on emotion
        if emotion == Emotion.ANGRY:
            rate = "105%"
            pitch = "+2st"
            volume = "loud"
        elif emotion == Emotion.HAPPY:
            rate = "105%"
            pitch = "+1st"
        elif emotion == Emotion.SAD:
            rate = "92%"
            pitch = "-1st"
            volume = "soft"
        elif emotion == Emotion.FEAR:
            rate = "110%"
            pitch = "+3st"
            volume = "soft"
        elif emotion == Emotion.SURPRISED:
            rate = "108%"
            pitch = "+2st"
        elif emotion == Emotion.DISGUST:
            rate = "95%"
            pitch = "-2st"
        
        # Style overrides
        if style == SSMLStyle.WHISPERED:
            rate = "95%"
            volume = "x-soft"
        elif style == SSMLStyle.SHOUTED:
            rate = "110%"
            pitch = "+3st"
            volume = "x-loud"
        elif style == SSMLStyle.URGENT:
            rate = "115%"
        elif style == SSMLStyle.CALM:
            rate = "92%"
            pitch = "-1st"
        elif style == SSMLStyle.NARRATION:
            rate = "98%"
        
        # Build SSML
        ssml = f"""<speak>
  <prosody rate="{rate}" pitch="{pitch}" volume="{volume}">
    {text}
  </prosody>
</speak>"""
        
        return ssml
    
    def synthesize(
        self,
        ssml: str,
        voice_name: str = "en-US-Neural2-C",
        language_code: str = "en-US"
    ) -> Optional[str]:
        """
        Synthesize SSML to audio file and return URL.
        
        Args:
            ssml: SSML-formatted text
            voice_name: Google Cloud voice name (default: Neural2-C, feminine)
            language_code: Language code (default: en-US)
        
        Returns:
            URL to the generated audio file, or None if synthesis failed
        """
        if not self.client:
            logger.error("TTS client not initialized")
            return None
        
        try:
            # Configure synthesis input
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
            
            # Configure voice parameters
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            # Configure audio output
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            # Perform synthesis
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Generate unique filename
            filename = f"{uuid.uuid4()}.mp3"
            file_path = Path(settings.media_dir) / filename
            
            # Ensure media directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write audio file
            with open(file_path, "wb") as out:
                out.write(response.audio_content)
            
            # Build URL
            audio_url = f"{settings.media_base_url}/{filename}"
            
            logger.info(f"Synthesized audio: {filename} ({len(response.audio_content)} bytes)")
            return audio_url
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}", exc_info=True)
            return None
    
    def synthesize_with_emotion(
        self,
        text: str,
        emotion: Optional[Emotion] = None,
        style: Optional[SSMLStyle] = None,
        voice_name: str = "en-US-Neural2-C"
    ) -> Optional[str]:
        """
        Convenience method: build SSML from emotion and synthesize.
        
        Args:
            text: Plain text utterance
            emotion: Emotional state
            style: SSML style
            voice_name: Voice preset
        
        Returns:
            URL to generated audio file
        """
        ssml = self.build_ssml(text, emotion, style)
        return self.synthesize(ssml, voice_name)


# Predefined voice presets for common NPC archetypes
VOICE_PRESETS = {
    "feminine_calm": "en-US-Neural2-C",
    "feminine_young": "en-US-Neural2-F",
    "masculine_deep": "en-US-Neural2-D",
    "masculine_casual": "en-US-Neural2-A",
    "elderly_wise": "en-GB-Neural2-B",
    "mysterious": "en-GB-Neural2-D",
}


def get_voice_for_preset(preset: Optional[str]) -> str:
    """
    Get Google Cloud voice name from preset string.
    
    Args:
        preset: Voice preset name
    
    Returns:
        Google Cloud voice name
    """
    if preset and preset in VOICE_PRESETS:
        return VOICE_PRESETS[preset]
    return "en-US-Neural2-C"  # Default


# Global TTS client instance
tts_client = TTSClient()


def synthesize_ssml(
    ssml: str,
    voice_name: str = "en-US-Neural2-C"
) -> Optional[str]:
    """
    Convenience function for synthesizing SSML.
    This is what the FastAPI endpoint calls.
    
    Args:
        ssml: SSML-formatted text
        voice_name: Google Cloud voice name
    
    Returns:
        URL to generated audio file
    """
    return tts_client.synthesize(ssml, voice_name)


def synthesize_from_response(
    text: str,
    emotion: Optional[Emotion] = None,
    voice_preset: Optional[str] = None,
    ssml_style: Optional[SSMLStyle] = None
) -> Optional[str]:
    """
    Synthesize audio from NPC response fields.
    
    Args:
        text: The utterance
        emotion: NPC emotion
        voice_preset: Voice preset name
        ssml_style: SSML style
    
    Returns:
        URL to generated audio file
    """
    voice_name = get_voice_for_preset(voice_preset)
    return tts_client.synthesize_with_emotion(text, emotion, ssml_style, voice_name)

