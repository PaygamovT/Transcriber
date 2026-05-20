import base64
import time
import os
import logging
import requests
from typing import Dict, Any, Optional

# Setup logging
logger = logging.getLogger("transcriber.transcription")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class TranscriptionService:
    """Service to interact with the OpenRouter transcription API."""
    
    def __init__(self, api_key: str, model: str = "google/gemini-flash-1.5"):
        logger.debug("TranscriptionService.__init__ entering")
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://openrouter.ai/api/v1/audio/transcriptions"
        logger.debug(f"TranscriptionService initialized with model: {self.model}")
        logger.debug("TranscriptionService.__init__ exiting successfully")

    def transcribe(self, wav_bytes: bytes) -> str:
        """Sends WAV audio bytes to OpenRouter for transcription.
        
        Args:
            wav_bytes: Raw bytes of the audio file in WAV format.
            
        Returns:
            The transcribed text.
            
        Raises:
            ValueError: If api_key is missing or wav_bytes is empty.
            requests.RequestException: If the API request fails.
        """
        logger.debug("TranscriptionService.transcribe entering")
        
        if not self.api_key:
            logger.error("API Key is missing")
            raise ValueError("OpenRouter API key is missing. Please set it in Settings.")
            
        if not wav_bytes:
            logger.error("Audio data is empty")
            raise ValueError("Audio data is empty")

        # Encode bytes to base64 string
        logger.debug("Encoding WAV bytes to Base64")
        base64_audio = base64.b64encode(wav_bytes).decode("utf-8")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input_audio": {
                "data": base64_audio,
                "format": "wav"
            }
        }
        
        # Mask API key for secure logging
        masked_key = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "..."
        logger.info(f"Sending transcription request to {self.endpoint}")
        logger.debug(f"Request payload summary: model={self.model}, audio_length_b64={len(base64_audio)} chars, API_key={masked_key}")
        
        start_time = time.time()
        try:
            response = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
            latency = time.time() - start_time
            logger.info(f"Transcription response received in {latency:.2f} seconds with status code {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            transcribed_text = result.get("text", "")
            
            logger.debug(f"Transcription result: '{transcribed_text}'")
            return transcribed_text
            
        except requests.RequestException as e:
            latency = time.time() - start_time
            logger.error(f"HTTP Request failed after {latency:.2f}s: {e}", exc_info=True)
            # If there's response body, log it for debugging
            if 'response' in locals() and response is not None:
                try:
                    logger.error(f"Error response body: {response.text}")
                except Exception:
                    pass
            raise
        finally:
            logger.debug("TranscriptionService.transcribe exiting")
