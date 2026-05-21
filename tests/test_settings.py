import sys
from unittest.mock import MagicMock, patch

# 1. Create and inject mock PyQt6 modules before importing settings to avoid ModuleNotFoundError
class MockQObject:
    def __init__(self, *args, **kwargs):
        pass

class MockQDialog(MockQObject):
    def __init__(self, parent=None):
        super().__init__()
        self._accepted = False
        self._rejected = False
        self._stylesheet = ""
        self._attributes = {}
    def setWindowTitle(self, title):
        self.title = title
    def setMinimumSize(self, w, h):
        self.min_w, self.min_h = w, h
    def setAttribute(self, attr, value=True):
        self._attributes[attr] = value
    def setStyleSheet(self, style):
        self._stylesheet = style
    def accept(self):
        self._accepted = True
    def reject(self):
        self._rejected = True

mock_pyqt6 = MagicMock()
mock_core = MagicMock()
mock_widgets = MagicMock()

mock_pyqt6.QtCore = mock_core
mock_pyqt6.QtWidgets = mock_widgets

mock_widgets.QDialog = MockQDialog
mock_core.Qt.WidgetAttribute.WA_DeleteOnClose = "WA_DeleteOnClose"

sys.modules["PyQt6"] = mock_pyqt6
sys.modules["PyQt6.QtCore"] = mock_core
sys.modules["PyQt6.QtWidgets"] = mock_widgets

# 2. Now import our UI component
import pytest
from src.ui.settings import SettingsDialog

def test_settings_dialog_initialization():
    """Test dialog initialization and default attributes."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "provider": "openrouter",
        "api_key": "dummy-key",
        "model": "google/gemini-3.1-flash-lite",
        "openrouter_api_key": "dummy-key",
        "openrouter_model": "google/gemini-3.1-flash-lite",
        "openai_api_key": "openai-key",
        "openai_model": "whisper-1",
        "groq_api_key": "groq-key",
        "groq_model": "whisper-large-v3",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "transcribe precisely"
    }.get(key, "")
    
    # Patch all QtWidgets elements inside setup_ui to inspect initialization
    with patch("src.ui.settings.QVBoxLayout"), \
         patch("src.ui.settings.QHBoxLayout"), \
         patch("src.ui.settings.QLabel") as mock_qlabel, \
         patch("src.ui.settings.QLineEdit") as mock_lineedit, \
         patch("src.ui.settings.QComboBox") as mock_combobox, \
         patch("src.ui.settings.QPushButton"), \
         patch("src.ui.settings.QFormLayout"), \
         patch("src.ui.settings.QGroupBox"):
         
        # Configure QComboBox mock to return valid integer indices for findText and findData
        mock_combobox.return_value.findText.return_value = 0
        mock_combobox.return_value.findData.return_value = 0
        mock_combobox.return_value.currentData.return_value = "openrouter"
        mock_combobox.return_value.currentText.return_value = "google/gemini-3.1-flash-lite"
        
        dialog = SettingsDialog(config=mock_config)
        
        # Verify basic parameters
        assert dialog.title == "Настройки Transcriber"
        assert dialog.min_w == 540
        assert dialog.min_h == 480
        assert dialog._attributes["WA_DeleteOnClose"] == True
        assert len(dialog._stylesheet) > 0

def test_settings_dialog_provider_switching():
    """Test switching between providers in the Settings dialog."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "provider": "openrouter",
        "openrouter_api_key": "or-key",
        "openrouter_model": "google/gemini-3.1-flash-lite",
        "openai_api_key": "oa-key",
        "openai_model": "whisper-1",
        "groq_api_key": "g-key",
        "groq_model": "whisper-large-v3"
    }.get(key, "")

    with patch("src.ui.settings.QVBoxLayout"), \
         patch("src.ui.settings.QHBoxLayout"), \
         patch("src.ui.settings.QLabel"), \
         patch("src.ui.settings.QLineEdit") as mock_lineedit, \
         patch("src.ui.settings.QComboBox") as mock_combobox, \
         patch("src.ui.settings.QPushButton"), \
         patch("src.ui.settings.QFormLayout"), \
         patch("src.ui.settings.QGroupBox"):

        mock_combobox.return_value.findText.return_value = -1
        mock_combobox.return_value.findData.return_value = -1
        mock_combobox.return_value.currentData.return_value = "openrouter"
        mock_combobox.return_value.currentText.return_value = "google/gemini-3.1-flash-lite"

        dialog = SettingsDialog(config=mock_config)

        # Mock the interactive GUI elements to inspect changes
        mock_api_key_label = MagicMock()
        mock_api_key_input = MagicMock()
        mock_model_combo = MagicMock()
        mock_model_combo.findText.return_value = -1
        mock_provider_combo = MagicMock()

        dialog.api_key_label = mock_api_key_label
        dialog.api_key_input = mock_api_key_input
        dialog.model_combo = mock_model_combo
        dialog.provider_combo = mock_provider_combo

        # 1. Switch to OpenAI
        mock_provider_combo.currentData.return_value = "openai"
        mock_api_key_input.text.return_value = "typed-or-key"
        mock_model_combo.currentText.return_value = "google/gemini-3.1-flash-lite"


        dialog.on_provider_changed()

        # Check that old provider values were temporarily cached
        assert dialog.temp_settings["openrouter"]["api_key"] == "typed-or-key"
        assert dialog.temp_settings["openrouter"]["model"] == "google/gemini-3.1-flash-lite"

        # Verify UI updates for new provider (OpenAI)
        mock_api_key_label.setText.assert_called_with("API Key OpenAI")
        mock_api_key_input.setPlaceholderText.assert_called_with("Enter your API Key...")
        mock_api_key_input.setText.assert_called_with("oa-key")
        mock_model_combo.clear.assert_called()

def test_settings_dialog_save():
    """Test saving settings from UI fields back to ConfigManager."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "provider": "openrouter",
        "openrouter_api_key": "dummy-key",
        "openrouter_model": "google/gemini-3.1-flash-lite",
        "openai_api_key": "",
        "openai_model": "whisper-1",
        "groq_api_key": "",
        "groq_model": "whisper-large-v3",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "transcribe precisely"
    }.get(key, "")
    
    with patch("src.ui.settings.QVBoxLayout"), \
         patch("src.ui.settings.QHBoxLayout"), \
         patch("src.ui.settings.QLabel"), \
         patch("src.ui.settings.QLineEdit") as mock_lineedit, \
         patch("src.ui.settings.QComboBox") as mock_combobox, \
         patch("src.ui.settings.QPushButton"), \
         patch("src.ui.settings.QFormLayout"), \
         patch("src.ui.settings.QGroupBox"):
         
        # Configure QComboBox mock to return valid integer indices for findText and findData
        mock_combobox.return_value.findText.return_value = 0
        mock_combobox.return_value.findData.return_value = 0
        mock_combobox.return_value.currentData.return_value = "openrouter"
        mock_combobox.return_value.currentText.return_value = "google/gemini-3.1-flash-lite"
        
        # Set up mock UI elements
        mock_api_key_input = MagicMock()
        mock_api_key_input.text.return_value = " new-api-key "
        
        mock_model_combo = MagicMock()
        mock_model_combo.currentText.return_value = " new-model "
        
        mock_provider_combo = MagicMock()
        mock_provider_combo.currentData.return_value = "openai"
        
        mock_hotkey_input = MagicMock()
        mock_hotkey_input.text.return_value = " <ctrl>+<shift>+z "
        
        mock_mode_combo = MagicMock()
        mock_mode_combo.currentData.return_value = "typewriter"
        
        mock_transcription_mode_combo = MagicMock()
        mock_transcription_mode_combo.currentData.return_value = "clean"
        
        dialog = SettingsDialog(config=mock_config)
        
        # Override constructed properties with our mock controls
        dialog.api_key_input = mock_api_key_input
        dialog.model_combo = mock_model_combo
        dialog.provider_combo = mock_provider_combo
        dialog.hotkey_input = mock_hotkey_input
        dialog.mode_combo = mock_mode_combo
        dialog.transcription_mode_combo = mock_transcription_mode_combo
        
        # Save
        dialog.save_settings()
        
        # Verify config update calls
        mock_config.set.assert_any_call("provider", "openai")
        mock_config.set.assert_any_call("openai_api_key", "new-api-key")
        mock_config.set.assert_any_call("openai_model", "new-model")
        mock_config.set.assert_any_call("hotkey", "<ctrl>+<shift>+z")
        mock_config.set.assert_any_call("insert_mode", "typewriter")
        mock_config.set.assert_any_call("transcription_mode", "clean")
        
        assert dialog._accepted == True


