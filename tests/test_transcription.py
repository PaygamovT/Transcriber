import pytest
import requests
from unittest.mock import patch, MagicMock
from src.services.transcription import TranscriptionService

def test_transcribe_success_gemini_normal():
    """Test successful normal transcription using Gemini model (routes to /chat/completions)."""
    service = TranscriptionService(api_key="valid-test-key", model="google/gemini-3.1-flash-lite")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "hello world from gemini"
                }
            }
        ]
    }
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="normal")
        
        assert result == "hello world from gemini"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer valid-test-key"
        assert kwargs["json"]["model"] == "google/gemini-3.1-flash-lite"
        
        user_msg = kwargs["json"]["messages"][0]
        assert user_msg["role"] == "user"
        assert user_msg["content"][0]["type"] == "text"
        assert "precise speech-to-text transcriber" in user_msg["content"][0]["text"]
        assert user_msg["content"][1]["type"] == "input_audio"
        assert user_msg["content"][1]["input_audio"]["format"] == "wav"

def test_transcribe_success_whisper_normal():
    """Test successful normal transcription using Whisper model (routes to /audio/transcriptions)."""
    service = TranscriptionService(api_key="valid-test-key", model="openai/whisper-large-v3")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello world from whisper"}
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="normal")
        
        assert result == "hello world from whisper"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://openrouter.ai/api/v1/audio/transcriptions"
        assert kwargs["headers"]["Authorization"] == "Bearer valid-test-key"
        assert kwargs["json"]["model"] == "openai/whisper-large-v3"
        assert "data" in kwargs["json"]["input_audio"]
        assert kwargs["json"]["input_audio"]["format"] == "wav"

def test_transcribe_success_gemini_normal_custom_prompt():
    """Test Gemini normal transcription with a custom system prompt."""
    service = TranscriptionService(
        api_key="valid-test-key", 
        model="google/gemini-3.1-flash-lite",
        system_prompt="Custom transcription instruction."
    )
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "custom prompt response"
                }
            }
        ]
    }
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="normal")
        
        assert result == "custom prompt response"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        user_msg = kwargs["json"]["messages"][0]
        assert user_msg["content"][0]["text"] == "Custom transcription instruction."

def test_transcribe_missing_api_key():
    """Test that transcribing with an empty API key raises ValueError."""
    service = TranscriptionService(api_key="", model="google/gemini-3.1-flash-lite")
    with pytest.raises(ValueError, match="OpenRouter API key is missing"):
        service.transcribe(b"some audio data")

def test_transcribe_empty_audio():
    """Test that transcribing with empty audio bytes raises ValueError."""
    service = TranscriptionService(api_key="some-key", model="google/gemini-3.1-flash-lite")
    with pytest.raises(ValueError, match="Audio data is empty"):
        service.transcribe(b"")

def test_transcribe_api_error():
    """Test that a non-200 HTTP status code raises requests.RequestException."""
    service = TranscriptionService(api_key="valid-test-key", model="google/gemini-3.1-flash-lite")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.RequestException("Unauthorized")
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        with pytest.raises(requests.RequestException):
            service.transcribe(dummy_wav_bytes)

def test_transcribe_clean_mode():
    """Test clean mode transcription payload and response parsing."""
    service = TranscriptionService(api_key="valid-test-key", model="google/gemini-3.1-flash-lite")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Привет, как дела?"
                }
            }
        ]
    }
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="clean")
        
        assert result == "Привет, как дела?"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer valid-test-key"
        assert kwargs["json"]["model"] == "google/gemini-3.1-flash-lite"
        assert "messages" in kwargs["json"]
        
        user_msg = kwargs["json"]["messages"][0]
        assert user_msg["role"] == "user"
        assert user_msg["content"][0]["type"] == "text"
        assert "clean up the text to make it read perfectly" in user_msg["content"][0]["text"]
        assert user_msg["content"][1]["type"] == "input_audio"
        assert user_msg["content"][1]["input_audio"]["format"] == "wav"

def test_transcribe_translate_mode():
    """Test translate mode transcription payload and response parsing."""
    service = TranscriptionService(api_key="valid-test-key", model="google/gemini-3.1-flash-lite")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello, how are you?"
                }
            }
        ]
    }
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="translate")
        
        assert result == "Hello, how are you?"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer valid-test-key"
        assert kwargs["json"]["model"] == "google/gemini-3.1-flash-lite"
        
        user_msg = kwargs["json"]["messages"][0]
        assert user_msg["role"] == "user"
        assert user_msg["content"][0]["type"] == "text"
        assert "translate it into natural, fluent English" in user_msg["content"][0]["text"]
        assert user_msg["content"][1]["type"] == "input_audio"
        assert user_msg["content"][1]["input_audio"]["format"] == "wav"

def test_transcribe_invalid_mode():
    """Test that an invalid mode raises ValueError."""
    service = TranscriptionService(api_key="valid-test-key", model="google/gemini-3.1-flash-lite")
    with pytest.raises(ValueError, match="Invalid transcription mode"):
        service.transcribe(b"RIFF....WAVEfmt...data...", mode="invalid")
