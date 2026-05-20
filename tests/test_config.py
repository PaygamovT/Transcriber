import json
import pytest
from pathlib import Path
from src.config import ConfigManager, DEFAULT_CONFIG

def test_default_config_loading(tmp_path):
    """Test that ConfigManager loads default values when no file exists."""
    config_dir = tmp_path / "config"
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    
    assert manager.get("api_key") == ""
    assert manager.get("model") == "google/gemini-flash-1.5"
    assert manager.get("hotkey") == "<ctrl>+<shift>+space"
    assert manager.get("audio_duration_limit") == 30
    assert manager.get("insert_mode") == "clipboard"
    
    # Assert it created the default file on disk
    config_file = config_dir / "config.json"
    assert config_file.exists()
    
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["model"] == "google/gemini-flash-1.5"

def test_set_and_get_config(tmp_path):
    """Test that values can be set and are persisted to disk."""
    config_dir = tmp_path / "config"
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    
    manager.set("api_key", "test-key-123")
    manager.set("insert_mode", "typewriter")
    
    assert manager.get("api_key") == "test-key-123"
    assert manager.get("insert_mode") == "typewriter"
    
    # Load a new manager pointing to the same file and verify persistence
    new_manager = ConfigManager(config_dir=config_dir, filename="config.json")
    assert new_manager.get("api_key") == "test-key-123"
    assert new_manager.get("insert_mode") == "typewriter"

def test_validation_rules(tmp_path):
    """Test that invalid config inputs are validated and rejected."""
    config_dir = tmp_path / "config"
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    
    # Validation for duration (integer, positive)
    manager.set("audio_duration_limit", -5)
    assert manager.get("audio_duration_limit") == 30  # Should remain default
    
    manager.set("audio_duration_limit", "abc")
    assert manager.get("audio_duration_limit") == 30  # Should remain default
    
    manager.set("audio_duration_limit", 45)
    assert manager.get("audio_duration_limit") == 45  # Should accept positive int
    
    # Validation for insert_mode
    manager.set("insert_mode", "invalid_mode")
    assert manager.get("insert_mode") == "clipboard"  # Should remain default

def test_corrupted_file_fallback(tmp_path):
    """Test that ConfigManager falls back to defaults when loading a corrupted file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    
    # Write corrupted JSON to file
    with open(config_file, "w", encoding="utf-8") as f:
        f.write("{invalid json")
        
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    assert manager.get("model") == "google/gemini-flash-1.5"
