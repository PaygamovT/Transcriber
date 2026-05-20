import pytest
import requests
from unittest.mock import patch, MagicMock
from src.services.transcription import TranscriptionService

def test_transcribe_success():
    """Test successful transcription call returning text."""
    service = TranscriptionService(api_key="valid-test-key", model="google/gemini-flash-1.5")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello world"}
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes)
        
        assert result == "hello world"
        mock_post.assert_called_once()
        # Verify call arguments
        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer valid-test-key"
        assert kwargs["json"]["model"] == "google/gemini-flash-1.5"
        assert "data" in kwargs["json"]["input_audio"]
        assert kwargs["json"]["input_audio"]["format"] == "wav"

def test_transcribe_missing_api_key():
    """Test that transcribing with an empty API key raises ValueError."""
    service = TranscriptionService(api_key="", model="google/gemini-flash-1.5")
    with pytest.raises(ValueError, match="OpenRouter API key is missing"):
        service.transcribe(b"some audio data")

def test_transcribe_empty_audio():
    """Test that transcribing with empty audio bytes raises ValueError."""
    service = TranscriptionService(api_key="some-key", model="google/gemini-flash-1.5")
    with pytest.raises(ValueError, match="Audio data is empty"):
        service.transcribe(b"")

def test_transcribe_api_error():
    """Test that a non-200 HTTP status code raises requests.RequestException."""
    service = TranscriptionService(api_key="valid-test-key", model="google/gemini-flash-1.5")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.RequestException("Unauthorized")
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        with pytest.raises(requests.RequestException):
            service.transcribe(dummy_wav_bytes)
