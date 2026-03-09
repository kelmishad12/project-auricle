"""
ElevenLabs text-to-speech integration.
"""
# pylint: disable=import-error,no-name-in-module
from typing import Protocol
import os
from elevenlabs.client import ElevenLabs

class AudioSynthesisProvider(Protocol):
    """Abstract protocol for text-to-speech generation."""
    def generate_audio_stream(self, text: str) -> bytes:
        """Generate audio stream bytes."""

class ElevenLabsService(AudioSynthesisProvider):
    """
    Concrete implementation of ElevenLabs Text-to-Speech using eleven_flash_v2_5.
    Designed for low-latency output briefings up to 5 minutes.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self.api_key:
            print("WARNING: ELEVENLABS_API_KEY not found. ElevenLabs API calls will fail.")

        self.client = ElevenLabs(api_key=self.api_key) if self.api_key else None
        self.model_id = "eleven_flash_v2_5"

    def generate_audio_stream(self, text: str) -> bytes:
        """Generate audio stream bytes using ElevenLabs API."""
        if not self.client:
            return b"Audio binary payload here... (Mocked - No API Key)"

        # Using 'JBFqnCBcs6qnNTcBWq7' (a widely used standard voice ID) or placeholder
        generator = self.client.text_to_speech.convert(
            text=text,
            voice_id="21m00Tcm4TlvDq8ikWAM", # Rachel voice ID standard
            model_id=self.model_id,
        )
        audio_bytes = b"".join(generator)
        return audio_bytes
