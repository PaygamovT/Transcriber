import json
import pytest
from pathlib import Path
from src.config import ConfigManager, DEFAULT_CONFIG

def test_default_config_loading(tmp_path):
    """Test that ConfigManager loads default values when no file exists."""
    config_dir = tmp_path / "config"
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    
    assert manager.get("provider") == "openrouter"
    assert manager.get("api_key") == ""
    assert manager.get("model") == "google/gemini-3.1-flash-lite"
    assert manager.get("openrouter_model") == "google/gemini-3.1-flash-lite"
    assert manager.get("openai_model") == "whisper-1"
    assert manager.get("groq_model") == "whisper-large-v3"
    assert manager.get("hotkey") == "<ctrl>+<shift>+<space>"
    assert manager.get("audio_duration_limit") == 30
    assert manager.get("insert_mode") == "typewriter"
    assert manager.get("transcription_mode") == "clean"
    
    # Assert it created the default file on disk
    config_file = config_dir / "config.json"
    assert config_file.exists()
    
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["provider"] == "openrouter"
    assert data["openrouter_model"] == "google/gemini-3.1-flash-lite"

def test_set_and_get_config(tmp_path):
    """Test that values can be set and are persisted to disk, covering dynamic mapping."""
    config_dir = tmp_path / "config"
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    
    # Test setting active provider values using legacy keys
    manager.set("api_key", "test-key-123")
    manager.set("insert_mode", "clipboard")
    
    assert manager.get("api_key") == "test-key-123"
    assert manager.get("openrouter_api_key") == "test-key-123"
    assert manager.get("insert_mode") == "clipboard"
    
    # Now switch provider to openai and verify independent settings
    manager.set("provider", "openai")
    assert manager.get("api_key") == ""  # openai API key should be empty by default
    assert manager.get("model") == "whisper-1"
    
    # Set openai specific values
    manager.set("api_key", "openai-key-abc")
    manager.set("model", "custom-openai-model")
    assert manager.get("api_key") == "openai-key-abc"
    assert manager.get("openai_api_key") == "openai-key-abc"
    assert manager.get("model") == "custom-openai-model"
    
    # Switch back to openrouter and verify original values are preserved
    manager.set("provider", "openrouter")
    assert manager.get("api_key") == "test-key-123"
    assert manager.get("model") == "google/gemini-3.1-flash-lite"
    
    # Load a new manager pointing to the same file and verify persistence
    new_manager = ConfigManager(config_dir=config_dir, filename="config.json")
    assert new_manager.get("provider") == "openrouter"
    assert new_manager.get("openrouter_api_key") == "test-key-123"
    assert new_manager.get("openai_api_key") == "openai-key-abc"

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
    assert manager.get("insert_mode") == "typewriter"  # Should remain default
    
    # Validation for transcription_mode
    manager.set("transcription_mode", "invalid_trans_mode")
    assert manager.get("transcription_mode") == "clean"  # Should remain default
    
    manager.set("transcription_mode", "clean")
    assert manager.get("transcription_mode") == "clean"  # Should accept valid mode

def test_corrupted_file_fallback(tmp_path):
    """Test that ConfigManager falls back to defaults when loading a corrupted file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    
    # Write corrupted JSON to file
    with open(config_file, "w", encoding="utf-8") as f:
        f.write("{invalid json")
        
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    assert manager.get("provider") == "openrouter"
    assert manager.get("openrouter_model") == "google/gemini-3.1-flash-lite"

def test_legacy_schema_migration(tmp_path):
    """Test that ConfigManager automatically migrates legacy schema to multi-provider schema."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    
    # Write legacy schema to file
    legacy_data = {
        "api_key": "legacy-key-999",
        "model": "google/gemini-flash-1.5",
        "insert_mode": "clipboard",
        "audio_duration_limit": 20
    }
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)
        
    manager = ConfigManager(config_dir=config_dir, filename="config.json")
    
    # Assert smart migrations occurred
    assert manager.get("provider") == "openrouter"
    assert manager.get("openrouter_api_key") == "legacy-key-999"
    # assert gemini-flash-1.5 upgraded to gemini-3.1-flash-lite
    assert manager.get("openrouter_model") == "google/gemini-3.1-flash-lite"
    # assert insert_mode upgraded from default clipboard to typewriter for legacy migration
    assert manager.get("insert_mode") == "typewriter"
    assert manager.get("audio_duration_limit") == 20  # User setting preserved
    
    # Ensure it's persisted back to disk in correct format
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "api_key" not in data  # Legacy keys removed from root
    assert "model" not in data
    assert data["provider"] == "openrouter"
    assert data["openrouter_api_key"] == "legacy-key-999"
    assert data["openrouter_model"] == "google/gemini-3.1-flash-lite"

