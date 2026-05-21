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
    "api_key": "",
    "model": "google/gemini-3.1-flash-lite",
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
                
            # Fill missing keys with defaults to ensure schema compatibility
            self.config_data = DEFAULT_CONFIG.copy()
            for key, val in loaded_data.items():
                if key in DEFAULT_CONFIG:
                    self.config_data[key] = val
                    logger.debug(f"Loaded config: {key} = {val}")
                else:
                    logger.warning(f"Ignored unexpected config key: {key}")
            
            # Upgrade deprecated default model to the new working model
            if self.config_data.get("model") == "google/gemini-flash-1.5":
                logger.info("Upgrading deprecated model google/gemini-flash-1.5 to google/gemini-3.1-flash-lite")
                self.config_data["model"] = "google/gemini-3.1-flash-lite"
                # Also upgrade default insert mode for returning users who were on the old default
                if self.config_data.get("insert_mode") == "clipboard":
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
        """Retrieves a configuration value."""
        logger.debug(f"ConfigManager.get entering for key: {key}")
        val = self.config_data.get(key, DEFAULT_CONFIG.get(key))
        logger.debug(f"ConfigManager.get exiting for key: {key} returning: {val}")
        return val

    def set(self, key: str, value: Any) -> None:
        """Sets a configuration value and triggers a save."""
        logger.debug(f"ConfigManager.set entering for key: {key}, value: {value}")
        
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
