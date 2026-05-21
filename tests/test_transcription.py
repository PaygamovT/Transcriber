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
        assert "pure audio transcription tool" in user_msg["content"][0]["text"]
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

def test_transcribe_success_openai_normal():
    """Test standard normal transcription with OpenAI (multipart Whisper)."""
    service = TranscriptionService(api_key="openai-test-key", model="whisper-1", provider="openai")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello from openai whisper"}
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="normal")
        
        assert result == "hello from openai whisper"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.openai.com/v1/audio/transcriptions"
        assert kwargs["headers"]["Authorization"] == "Bearer openai-test-key"
        assert kwargs["data"]["model"] == "whisper-1"
        assert "file" in kwargs["files"]
        assert kwargs["files"]["file"][0] == "audio.wav"
        assert kwargs["files"]["file"][1] == dummy_wav_bytes
        assert kwargs["files"]["file"][2] == "audio/wav"

def test_transcribe_success_groq_normal():
    """Test standard normal transcription with Groq (multipart Whisper)."""
    service = TranscriptionService(api_key="groq-test-key", model="whisper-large-v3", provider="groq")
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello from groq whisper"}
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="normal")
        
        assert result == "hello from groq whisper"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.groq.com/openai/v1/audio/transcriptions"
        assert kwargs["headers"]["Authorization"] == "Bearer groq-test-key"
        assert kwargs["data"]["model"] == "whisper-large-v3"
        assert "file" in kwargs["files"]

def test_transcribe_openai_clean_mode_pipeline():
    """Test the two-step clean mode pipeline on OpenAI (Whisper + Chat Completion)."""
    service = TranscriptionService(
        api_key="openai-test-key", 
        model="whisper-1", 
        provider="openai", 
        chat_model="gpt-4o-mini"
    )
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    # Mock responses for the two steps
    mock_stt_response = MagicMock()
    mock_stt_response.status_code = 200
    mock_stt_response.json.return_value = {"text": "привет привет э-э"}
    
    mock_chat_response = MagicMock()
    mock_chat_response.status_code = 200
    mock_chat_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Привет"
                }
            }
        ]
    }
    
    def side_effect(url, *args, **kwargs):
        if "audio/transcriptions" in url:
            return mock_stt_response
        elif "chat/completions" in url:
            return mock_chat_response
        raise ValueError(f"Unexpected URL: {url}")
        
    with patch("requests.post", side_effect=side_effect) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="clean")
        
        assert result == "Привет"
        assert mock_post.call_count == 2
        
        # Verify first call (STT)
        first_call = mock_post.call_args_list[0]
        assert first_call[0][0] == "https://api.openai.com/v1/audio/transcriptions"
        
        # Verify second call (Chat Completion cleanup)
        second_call = mock_post.call_args_list[1]
        assert second_call[0][0] == "https://api.openai.com/v1/chat/completions"
        assert second_call[1]["json"]["model"] == "gpt-4o-mini"
        assert second_call[1]["json"]["messages"][1]["content"] == "привет привет э-э"
        assert "clean up the provided text" in second_call[1]["json"]["messages"][0]["content"]

def test_transcribe_groq_translate_mode_pipeline():
    """Test the two-step translate mode pipeline on Groq (Whisper + Chat Completion)."""
    service = TranscriptionService(
        api_key="groq-test-key", 
        model="whisper-large-v3", 
        provider="groq", 
        chat_model="llama3-8b-8192"
    )
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    # Mock responses for the two steps
    mock_stt_response = MagicMock()
    mock_stt_response.status_code = 200
    mock_stt_response.json.return_value = {"text": "привет"}
    
    mock_chat_response = MagicMock()
    mock_chat_response.status_code = 200
    mock_chat_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello"
                }
            }
        ]
    }
    
    def side_effect(url, *args, **kwargs):
        if "audio/transcriptions" in url:
            return mock_stt_response
        elif "chat/completions" in url:
            return mock_chat_response
        raise ValueError(f"Unexpected URL: {url}")
        
    with patch("requests.post", side_effect=side_effect) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="translate")
        
        assert result == "Hello"
        assert mock_post.call_count == 2
        
        # Verify first call
        first_call = mock_post.call_args_list[0]
        assert first_call[0][0] == "https://api.groq.com/openai/v1/audio/transcriptions"
        
        # Verify second call
        second_call = mock_post.call_args_list[1]
        assert second_call[0][0] == "https://api.groq.com/openai/v1/chat/completions"
        assert second_call[1]["json"]["model"] == "llama3-8b-8192"
        assert second_call[1]["json"]["messages"][1]["content"] == "привет"
        assert "translate it into natural, fluent English" in second_call[1]["json"]["messages"][0]["content"]

def test_transcribe_pipeline_chat_failure_fallback():
    """Test that if the second chat completion step fails, we gracefully fall back to raw transcription."""
    service = TranscriptionService(
        api_key="openai-test-key", 
        model="whisper-1", 
        provider="openai", 
        chat_model="gpt-4o-mini"
    )
    dummy_wav_bytes = b"RIFF....WAVEfmt...data..."
    
    mock_stt_response = MagicMock()
    mock_stt_response.status_code = 200
    mock_stt_response.json.return_value = {"text": "raw transcription"}
    
    def side_effect(url, *args, **kwargs):
        if "audio/transcriptions" in url:
            return mock_stt_response
        elif "chat/completions" in url:
            raise requests.RequestException("Chat completion service down")
        raise ValueError(f"Unexpected URL: {url}")
        
    with patch("requests.post", side_effect=side_effect) as mock_post:
        result = service.transcribe(dummy_wav_bytes, mode="clean")
        
        # Should gracefully return raw transcript
        assert result == "raw transcription"
        assert mock_post.call_count == 2

