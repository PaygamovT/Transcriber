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
        "api_key": "dummy-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "transcribe precisely"
    }[key]
    
    # Patch all QtWidgets elements inside setup_ui to inspect initialization
    with patch("src.ui.settings.QVBoxLayout"), \
         patch("src.ui.settings.QHBoxLayout"), \
         patch("src.ui.settings.QLabel"), \
         patch("src.ui.settings.QLineEdit") as mock_lineedit, \
         patch("src.ui.settings.QTextEdit") as mock_textedit, \
         patch("src.ui.settings.QSpinBox") as mock_spinbox, \
         patch("src.ui.settings.QComboBox") as mock_combobox, \
         patch("src.ui.settings.QPushButton"), \
         patch("src.ui.settings.QFormLayout"), \
         patch("src.ui.settings.QGroupBox"):
         
        # Configure QComboBox mock to return valid integer indices for findText and findData
        mock_combobox.return_value.findText.return_value = 0
        mock_combobox.return_value.findData.return_value = 0
        
        dialog = SettingsDialog(config=mock_config)
        
        # Verify basic parameters
        assert dialog.title == "Настройки Transcriber"
        assert dialog.min_w == 480
        assert dialog.min_h == 480
        assert dialog._attributes["WA_DeleteOnClose"] == True
        assert len(dialog._stylesheet) > 0

def test_settings_dialog_save():
    """Test saving settings from UI fields back to ConfigManager."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "api_key": "dummy-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "transcribe precisely"
    }[key]
    
    with patch("src.ui.settings.QVBoxLayout"), \
         patch("src.ui.settings.QHBoxLayout"), \
         patch("src.ui.settings.QLabel"), \
         patch("src.ui.settings.QLineEdit") as mock_lineedit, \
         patch("src.ui.settings.QTextEdit") as mock_textedit, \
         patch("src.ui.settings.QSpinBox") as mock_spinbox, \
         patch("src.ui.settings.QComboBox") as mock_combobox, \
         patch("src.ui.settings.QPushButton"), \
         patch("src.ui.settings.QFormLayout"), \
         patch("src.ui.settings.QGroupBox"):
         
        # Configure QComboBox mock to return valid integer indices for findText and findData
        mock_combobox.return_value.findText.return_value = 0
        mock_combobox.return_value.findData.return_value = 0
        
        # Set up mock UI elements
        mock_api_key_input = MagicMock()
        mock_api_key_input.text.return_value = " new-api-key "
        
        mock_model_combo = MagicMock()
        mock_model_combo.currentText.return_value = " new-model "
        
        mock_hotkey_input = MagicMock()
        mock_hotkey_input.text.return_value = " <ctrl>+<shift>+z "
        
        mock_duration_spin = MagicMock()
        mock_duration_spin.value.return_value = 60
        
        mock_mode_combo = MagicMock()
        mock_mode_combo.currentData.return_value = "typewriter"
        
        mock_transcription_mode_combo = MagicMock()
        mock_transcription_mode_combo.currentData.return_value = "clean"
        
        mock_prompt_input = MagicMock()
        mock_prompt_input.toPlainText.return_value = " new prompt "
        
        dialog = SettingsDialog(config=mock_config)
        
        # Override constructed properties with our mock controls
        dialog.api_key_input = mock_api_key_input
        dialog.model_combo = mock_model_combo
        dialog.hotkey_input = mock_hotkey_input
        dialog.duration_spin = mock_duration_spin
        dialog.mode_combo = mock_mode_combo
        dialog.transcription_mode_combo = mock_transcription_mode_combo
        dialog.prompt_input = mock_prompt_input
        
        # Save
        dialog.save_settings()
        
        # Verify config update calls
        mock_config.set.assert_any_call("api_key", "new-api-key")
        mock_config.set.assert_any_call("model", "new-model")
        mock_config.set.assert_any_call("hotkey", "<ctrl>+<shift>+z")
        mock_config.set.assert_any_call("audio_duration_limit", 60)
        mock_config.set.assert_any_call("insert_mode", "typewriter")
        mock_config.set.assert_any_call("transcription_mode", "clean")
        mock_config.set.assert_any_call("system_prompt", "new prompt")
        
        assert dialog._accepted == True
