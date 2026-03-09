"""
Unit tests for Project Auricle Services.
"""
from unittest.mock import patch, MagicMock

from src.services.gemini import GeminiService
from src.services.elevenlabs import ElevenLabsService


def test_gemini_service_mocked():
    """Test GeminiService returns mocked response without API key."""
    service = GeminiService(credentials_path=None)
    content = service.generate_content("Hello")
    assert "Mocked" in content

    analysis = service.analyze_context({"briefing": "Test"})
    assert "Mock" in analysis["reasoning"]
    assert analysis["safety_passed"] is True


@patch("src.services.gemini.json.load")
@patch("src.services.gemini.vertexai.init")
@patch("src.services.gemini.GenerativeModel")
@patch("builtins.open")
def test_gemini_service_with_key(
        _mock_open, mock_model_class, _mock_vertexai_init, mock_json_load):
    """Test GeminiService with API key interacts with generativeai."""
    mock_json_load.return_value = {"project_id": "test"}
    # Setup mock response
    mock_response = MagicMock()
    mock_response.text = "Generated content"
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance

    service = GeminiService(credentials_path="TEST_KEY")
    content = service.generate_content("Hello")
    assert content == "Generated content"
    mock_instance.generate_content.assert_called_once_with("Hello")


def test_elevenlabs_service_mocked():
    """Test ElevenLabsService returns mocked response without API key."""
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
