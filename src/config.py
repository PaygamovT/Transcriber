import os
import json
import logging
from pathlib import Path
from typing import Any, Dict

# Setup logging
logger = logging.getLogger("transcriber.config")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "openrouter",
    "openrouter_api_key": "",
    "openrouter_model": "google/gemini-3.1-flash-lite",
    "openai_api_key": "",
    "openai_model": "whisper-1",
    "openai_chat_model": "gpt-4o-mini",
    "groq_api_key": "",
    "groq_model": "whisper-large-v3",
    "groq_chat_model": "llama3-8b-8192",
    "hotkey": "<ctrl>+<shift>+<space>",
    "system_prompt": (
        "You are a precise speech-to-text transcriber. "
        "Transcribe the audio exactly as spoken without adding any introductory or concluding remarks."
    ),
    "audio_duration_limit": 30,
    "insert_mode": "typewriter",
    "transcription_mode": "normal"
}

class ConfigManager:
    """Manages the application configuration, loading/saving to JSON."""
    
    def __init__(self, config_dir: Path = None, filename: str = "config.json"):
        logger.debug("ConfigManager.__init__ entering")
        
        if config_dir is None:
            # Default to ~/.transcriber
            self.config_dir = Path.home() / ".transcriber"
        else:
            self.config_dir = Path(config_dir)
            
        self.config_path = self.config_dir / filename
        logger.debug(f"Config path resolved to: {self.config_path}")
        
        self.config_data: Dict[str, Any] = {}
        self.load()
        
        logger.debug("ConfigManager.__init__ exiting successfully")
 
    def load(self) -> None:
        """Loads configuration from the JSON file, falling back to defaults if missing/invalid."""
        logger.debug("ConfigManager.load entering")
        
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}. Loading defaults.")
            self.config_data = DEFAULT_CONFIG.copy()
            self.save()
            return
 
        try:
            logger.debug(f"Attempting to read config from {self.config_path}")
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                
            if not isinstance(loaded_data, dict):
                raise ValueError("Config root must be a JSON object")
                
            # Smart migration for old schema:
            # If the loaded data has old 'api_key' or 'model' but no 'provider', migrate them to openrouter.
            legacy_api_key = loaded_data.get("api_key")
            legacy_model = loaded_data.get("model")
            has_provider = "provider" in loaded_data
            
            # Fill missing keys with defaults to ensure schema compatibility
            self.config_data = DEFAULT_CONFIG.copy()
            for key, val in loaded_data.items():
                if key in DEFAULT_CONFIG:
                    self.config_data[key] = val
                    logger.debug(f"Loaded config: {key} = {val}")
                else:
                    logger.warning(f"Ignored unexpected config key: {key}")
            
            # Apply migration if needed
            if not has_provider:
                logger.info("Migrating legacy config schema to multi-provider schema")
                if legacy_api_key is not None:
                    self.config_data["openrouter_api_key"] = legacy_api_key
                    logger.info("Migrated legacy API key to openrouter_api_key")
                if legacy_model is not None:
                    # Deprecated model upgrade check
                    if legacy_model == "google/gemini-flash-1.5":
                        legacy_model = "google/gemini-3.1-flash-lite"
                    self.config_data["openrouter_model"] = legacy_model
                    logger.info(f"Migrated legacy model to openrouter_model: {legacy_model}")
                self.config_data["provider"] = "openrouter"
                self.save()
            
            # Upgrade deprecated default model to the new working model (independent of schema migration)
            if self.config_data.get("openrouter_model") == "google/gemini-flash-1.5":
                logger.info("Upgrading deprecated model google/gemini-flash-1.5 to google/gemini-3.1-flash-lite")
                self.config_data["openrouter_model"] = "google/gemini-3.1-flash-lite"
                self.save()
                
            if self.config_data.get("insert_mode") == "clipboard" and not has_provider:
                # Upgrade default insert mode for returning users who were on the old default
                logger.info("Upgrading default insert_mode from clipboard to typewriter")
                self.config_data["insert_mode"] = "typewriter"
                self.save()
                    
            logger.info("Configuration successfully loaded from file")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}. Falling back to default settings.", exc_info=True)
            self.config_data = DEFAULT_CONFIG.copy()
            
        logger.debug("ConfigManager.load exiting")

    def save(self) -> None:
        """Saves current configuration to the JSON file."""
        logger.debug("ConfigManager.save entering")
        
        try:
            logger.debug(f"Ensuring config directory exists: {self.config_dir}")
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Writing configuration data to {self.config_path}")
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
                
            logger.info("Configuration successfully saved to disk")
        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_path}: {e}", exc_info=True)
            
        logger.debug("ConfigManager.save exiting")

    def get(self, key: str) -> Any:
        """Retrieves a configuration value, dynamically mapping legacy API keys/models to the active provider."""
        logger.debug(f"ConfigManager.get entering for key: {key}")
        if key == "api_key":
            provider = self.config_data.get("provider", "openrouter")
            val = self.config_data.get(f"{provider}_api_key", "")
        elif key == "model":
            provider = self.config_data.get("provider", "openrouter")
            val = self.config_data.get(f"{provider}_model", "")
        else:
            val = self.config_data.get(key, DEFAULT_CONFIG.get(key))
        logger.debug(f"ConfigManager.get exiting for key: {key} returning: {val}")
        return val

    def set(self, key: str, value: Any) -> None:
        """Sets a configuration value and triggers a save, mapping legacy key/model to the active provider."""
        logger.debug(f"ConfigManager.set entering for key: {key}, value: {value}")
        
        # Intercept legacy/dynamic keys and redirect to active provider
        if key == "api_key":
            provider = self.config_data.get("provider", "openrouter")
            key = f"{provider}_api_key"
        elif key == "model":
            provider = self.config_data.get("provider", "openrouter")
            key = f"{provider}_model"

        if key not in DEFAULT_CONFIG:
            logger.warning(f"Attempted to set custom/invalid configuration key: {key}")
            
        # Validation checks
        if key == "audio_duration_limit":
            try:
                value = int(value)
                if value <= 0:
                    raise ValueError("Duration limit must be positive")
            except (ValueError, TypeError) as e:
                logger.error(f"Validation error for {key}: {e}")
                return
                
        if key == "insert_mode" and value not in ("clipboard", "typewriter"):
            logger.error(f"Validation error for {key}: '{value}' is not a valid mode.")
            return

        if key == "transcription_mode" and value not in ("normal", "clean", "translate"):
            logger.error(f"Validation error for {key}: '{value}' is not a valid transcription mode.")
            return

        self.config_data[key] = value
        logger.info(f"Config updated: {key} = {value}")
        self.save()
        
        logger.debug("ConfigManager.set exiting")
