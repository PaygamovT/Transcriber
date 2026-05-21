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
    """Service to interact with OpenRouter, OpenAI, and Groq transcription APIs."""
    
    def __init__(self, api_key: str, model: str = "google/gemini-3.1-flash-lite", system_prompt: Optional[str] = None, provider: str = "openrouter", chat_model: Optional[str] = None):
        logger.debug("TranscriptionService.__init__ entering")
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.provider = provider or "openrouter"
        self.chat_model = chat_model
        self.endpoint = "https://openrouter.ai/api/v1/audio/transcriptions"
        logger.debug(f"TranscriptionService initialized with provider: {self.provider}, model: {self.model}")
        logger.debug("TranscriptionService.__init__ exiting successfully")
 
    def transcribe(self, wav_bytes: bytes, mode: str = "normal") -> str:
        """Sends WAV audio bytes to the active provider for transcription.
        
        Args:
            wav_bytes: Raw bytes of the audio file in WAV format.
            mode: The transcription mode ("normal", "clean", "translate").
            
        Returns:
            The transcribed (and potentially cleaned/translated) text.
            
        Raises:
            ValueError: If api_key is missing or wav_bytes is empty.
            requests.RequestException: If any API request fails.
        """
        logger.debug(f"TranscriptionService.transcribe entering. Provider: {self.provider}, Mode: {mode}")
        
        if not self.api_key:
            logger.error("API Key is missing")
            p_name = "OpenRouter" if self.provider == "openrouter" else ("OpenAI" if self.provider == "openai" else self.provider.capitalize())
            raise ValueError(f"{p_name} API key is missing. Please set it in Settings.")

            
        if not wav_bytes:
            logger.error("Audio data is empty")
            raise ValueError("Audio data is empty")
 
        if mode not in ("normal", "clean", "translate"):
            logger.error(f"Invalid mode passed: {mode}")
            raise ValueError(f"Invalid transcription mode: {mode}")
            
        # 1. Routing for standard OpenAI/Groq APIs
        if self.provider in ("openai", "groq"):
            base_url = "https://api.openai.com/v1" if self.provider == "openai" else "https://api.groq.com/openai/v1"
            
            # Step 1: Perform standard speech-to-text via audio/transcriptions endpoint using multipart/form-data
            url = f"{base_url}/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            files = {
                "file": ("audio.wav", wav_bytes, "audio/wav")
            }
            data = {
                "model": self.model
            }
            
            masked_key = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "..."
            logger.info(f"Sending {self.provider} transcription request to {url}")
            logger.debug(f"Request parameters: model={self.model}, audio_bytes={len(wav_bytes)}, API_key={masked_key}")
            
            start_time = time.time()
            try:
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
                latency = time.time() - start_time
                logger.info(f"Transcription response received in {latency:.2f} seconds with status code {response.status_code}")
                
                response.raise_for_status()
                result = response.json()
                transcribed_text = result.get("text", "").strip()
                
            except requests.RequestException as e:
                latency = time.time() - start_time
                logger.error(f"STT Request failed after {latency:.2f}s: {e}", exc_info=True)
                if 'response' in locals() and response is not None:
                    try:
                        logger.error(f"Error response body: {response.text}")
                    except Exception:
                        pass
                raise
                
            # Step 2: Handle advanced modes ("clean" / "translate") via a second LLM chat completion step
            if mode in ("clean", "translate"):
                chat_url = f"{base_url}/chat/completions"
                chat_model = self.chat_model
                if not chat_model:
                    chat_model = "gpt-4o-mini" if self.provider == "openai" else "llama3-8b-8192"
                
                if mode == "clean":
                    prompt = (
                        "You are an expert audio editor and speech transcriber. Your task is to clean up the provided text to make it read perfectly.\n"
                        "Specifically, you must:\n"
                        "1. Remove any duplicated/repeated words or phrases (e.g., if the user says \"привет привет\", output \"Привет\").\n"
                        "2. Remove all verbal stutters and filler sounds/filler words (like \"э-э\", \"м-м\", \"а-у\", \"как бы\", \"так сказать\").\n"
                        "3. Maintain a natural, correct, and fluent grammatical structure of the spoken language.\n"
                        "4. Output ONLY the clean text without any introductory or concluding remarks."
                    )
                else: # translate mode
                    prompt = (
                        "You are an expert translator and speech transcriber. Your task is to clean up the provided text completely, and translate it into natural, fluent English.\n"
                        "Specifically, you must:\n"
                        "1. Clean up the source speech by removing any duplicated/repeated words, stutters, and filler sounds.\n"
                        "2. Translate the cleaned speech directly into natural, grammatically correct English.\n"
                        "3. Output ONLY the final English translation without any introductory or concluding remarks."
                    )
                    
                chat_payload = {
                    "model": chat_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": prompt
                        },
                        {
                            "role": "user",
                            "content": transcribed_text
                        }
                    ]
                }
                
                chat_headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                logger.info(f"Sending advanced cleaning/translation chat completion to {chat_url} using model {chat_model}")
                try:
                    chat_start_time = time.time()
                    chat_response = requests.post(chat_url, headers=chat_headers, json=chat_payload, timeout=30)
                    chat_latency = time.time() - chat_start_time
                    logger.info(f"Chat completion received in {chat_latency:.2f}s with status code {chat_response.status_code}")
                    
                    chat_response.raise_for_status()
                    chat_result = chat_response.json()
                    choices = chat_result.get("choices", [])
                    if choices:
                        transcribed_text = choices[0].get("message", {}).get("content", "").strip()
                except requests.RequestException as e:
                    logger.error(f"Chat Completion cleanup failed: {e}", exc_info=True)
                    # We fall back to standard raw transcription if LLM cleanup step fails
                    logger.info("Falling back to raw transcription output")
                    
            logger.debug(f"Final transcription result: '{transcribed_text}'")
            return transcribed_text
            
        # 2. Legacy routing for OpenRouter API (base64 input_audio format)
        else:
            # Encode bytes to base64 string
            logger.debug("Encoding WAV bytes to Base64")
            base64_audio = base64.b64encode(wav_bytes).decode("utf-8")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # OpenRouter's /audio/transcriptions endpoint only supports dedicated speech-to-text models like Whisper.
            # If the model is a general-purpose chat/multimodal model (e.g., Gemini), we route all modes (including normal)
            # to /chat/completions.
            use_chat_endpoint = mode in ("clean", "translate") or "whisper" not in self.model.lower()
 
            if not use_chat_endpoint:
                url = self.endpoint
                payload = {
                    "model": self.model,
                    "input_audio": {
                        "data": base64_audio,
                        "format": "wav"
                    }
                }
            else:
                url = "https://openrouter.ai/api/v1/chat/completions"
                if mode == "clean":
                    prompt = (
                        "You are an expert audio editor and speech transcriber. Your task is to transcribe the speech from the provided audio, but clean up the text to make it read perfectly.\n"
                        "Specifically, you must:\n"
                        "1. Remove any duplicated/repeated words or phrases (e.g., if the user says \"привет привет\", output \"Привет\").\n"
                        "2. Remove all verbal stutters and filler sounds/filler words (like \"э-э\", \"м-м\", \"а-у\", \"как бы\", \"так сказать\").\n"
                        "3. Maintain a natural, correct, and fluent grammatical structure of the spoken language.\n"
                        "4. Output ONLY the clean transcription without any introductory or concluding remarks."
                    )
                elif mode == "translate":
                    prompt = (
                        "You are an expert translator and speech transcriber. Your task is to transcribe the speech from the provided audio, clean it up completely, and translate it into natural, fluent English.\n"
                        "Specifically, you must:\n"
                        "1. Clean up the source speech by removing any duplicated/repeated words, stutters, and filler sounds (like \"э-э\", \"а-у\").\n"
                        "2. Translate the cleaned speech directly into natural, grammatically correct English.\n"
                        "3. Output ONLY the final English translation without any introductory or concluding remarks."
                    )
                else:  # normal mode using chat completions
                    prompt = self.system_prompt or (
                        "You are a precise speech-to-text transcriber. "
                        "Transcribe the audio exactly as spoken without adding any introductory or concluding remarks."
                    )
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": base64_audio,
                                        "format": "wav"
                                    }
                                }
                            ]
                        }
                    ]
                }
            
            # Mask API key for secure logging
            masked_key = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "..."
            logger.info(f"Sending OpenRouter transcription request to {url} (Mode: {mode})")
            logger.debug(f"Request payload summary: model={self.model}, audio_length_b64={len(base64_audio)} chars, API_key={masked_key}")
            
            start_time = time.time()
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                latency = time.time() - start_time
                logger.info(f"Transcription response received in {latency:.2f} seconds with status code {response.status_code}")
                
                response.raise_for_status()
                result = response.json()
                
                if not use_chat_endpoint:
                    transcribed_text = result.get("text", "")
                else:
                    choices = result.get("choices", [])
                    if choices:
                        transcribed_text = choices[0].get("message", {}).get("content", "")
                    else:
                        transcribed_text = ""
                
                logger.debug(f"Transcription result: '{transcribed_text}'")
                return transcribed_text
                
            except requests.RequestException as e:
                latency = time.time() - start_time
                logger.error(f"HTTP Request failed after {latency:.2f}s: {e}", exc_info=True)
                if 'response' in locals() and response is not None:
                    try:
                        logger.error(f"Error response body: {response.text}")
                    except Exception:
                        pass
                raise
            finally:
                logger.debug("TranscriptionService.transcribe exiting")

