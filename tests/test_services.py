"""
Unit tests for Project Auricle Services.
"""
from unittest.mock import patch, MagicMock

from src.services.gemini import GeminiService
from src.services.elevenlabs import ElevenLabsService


def test_gemini_service_mocked():
    """Test GeminiService returns mocked response without API key."""
    with patch.dict('os.environ', clear=True):
        service = GeminiService()
        content = service.generate_content("Hello")
        assert "Mocked" in content

    analysis = service.analyze_context({"briefing": "Test"})
    assert "Mock" in analysis["reasoning"]
    assert analysis["safety_passed"] is True


@patch("src.services.gemini.genai.configure")
@patch("src.services.gemini.genai.GenerativeModel")
def test_gemini_service_with_key(mock_model_class, _mock_configure):
    """Test GeminiService with API key interacts with generativeai."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.text = "Generated content"
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    with patch.dict('os.environ', {'GEMINI_API_KEY': 'TEST_KEY'}):
        service = GeminiService()
        content = service.generate_content("Hello")
        assert content == "Generated content"
        mock_instance.generate_content.assert_called_once_with("Hello")


def test_elevenlabs_service_mocked():
    """Test ElevenLabsService returns mocked response without API key."""
    with patch.dict('os.environ', clear=True):
        service = ElevenLabsService(api_key=None)
        audio = service.generate_audio_stream("Hello")
        assert b"Mocked" in audio


@patch("src.services.elevenlabs.ElevenLabs")
def test_elevenlabs_service_with_key(mock_client):
    """Test ElevenLabsService with API key interacts with elevenlabs client."""
    mock_instance = MagicMock()
    mock_instance.text_to_speech.convert.return_value = [b"audio", b"_chunk"]
    mock_client.return_value = mock_instance

    service = ElevenLabsService(api_key="TEST_KEY")
    audio = service.generate_audio_stream("Hello")

    assert audio == b"audio_chunk"
    mock_instance.text_to_speech.convert.assert_called_once()
