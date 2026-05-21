import sys
from unittest.mock import MagicMock, patch

# 1. Setup comprehensive PyQt6 mock environment before importing components
class MockQObject:
    def __init__(self, *args, **kwargs):
        pass

class MockQDialog(MockQObject):
    def __init__(self, parent=None):
        super().__init__()
        self._attributes = {}
        self._accepted = False
        self._rejected = False
        self._stylesheet = ""
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
    def show(self):
        pass
    def activateWindow(self):
        pass
    def raise_(self):
        pass

class MockQSystemTrayIcon(MockQObject):
    class MessageIcon:
        Information = "Information"
        Warning = "Warning"
        Critical = "Critical"
        NoIcon = "NoIcon"

    class ActivationReason:
        DoubleClick = 2
        Trigger = 3

    def __init__(self, parent=None):
        super().__init__()
        self._visible = False
        self._tooltip = ""
        self._icon = None
        self._menu = None
        self._notification = None
        self.activated = MagicMock()
    def show(self):
        self._visible = True
    def setIcon(self, icon):
        self._icon = icon
    def setToolTip(self, tooltip):
        self._tooltip = tooltip
    def setContextMenu(self, menu):
        self._menu = menu
    def showMessage(self, title, message, icon_type, timeout):
        self._notification = (title, message, icon_type, timeout)

class MockQMenu(MockQObject):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._actions = []
        self._stylesheet = ""
    def addAction(self, action):
        self._actions.append(action)
    def addSeparator(self):
        self._actions.append("separator")
    def setStyleSheet(self, stylesheet):
        self._stylesheet = stylesheet

class MockQAction(MockQObject):
    def __init__(self, text, parent=None):
        super().__init__()
        self._text = text
        self._enabled = True
        self.triggered = MagicMock()
    def setEnabled(self, enabled):
        self._enabled = enabled
    def setText(self, text):
        self._text = text
    def text(self):
        return self._text

# Create mock structure
mock_pyqt6 = MagicMock()
mock_core = MagicMock()
mock_widgets = MagicMock()
mock_gui = MagicMock()

mock_pyqt6.QtCore = mock_core
mock_pyqt6.QtWidgets = mock_widgets
mock_pyqt6.QtGui = mock_gui

# Populate mock_widgets
mock_widgets.QDialog = MockQDialog
mock_widgets.QSystemTrayIcon = MockQSystemTrayIcon
mock_widgets.QMenu = MockQMenu
mock_widgets.QApplication = MagicMock()

# Populate mock_widgets with mock classes needed by SettingsDialog import
for name in [
    "QVBoxLayout", "QHBoxLayout", "QLabel", "QLineEdit", "QTextEdit", 
    "QSpinBox", "QComboBox", "QPushButton", "QFormLayout", "QGroupBox"
]:
    setattr(mock_widgets, name, MagicMock)

# Populate mock_gui
mock_gui.QAction = MockQAction
mock_gui.QIcon = MagicMock()
mock_gui.QPixmap = MagicMock()
mock_gui.QPainter = MagicMock()
mock_gui.QColor = MagicMock()

# Populate mock_core
mock_core.Qt.PenStyle.NoPen = "NoPen"
mock_core.Qt.WidgetAttribute.WA_DeleteOnClose = "WA_DeleteOnClose"
mock_core.pyqtSlot = lambda *args, **kwargs: lambda fn: fn

# Inject mock modules
sys.modules["PyQt6"] = mock_pyqt6
sys.modules["PyQt6.QtCore"] = mock_core
sys.modules["PyQt6.QtWidgets"] = mock_widgets
sys.modules["PyQt6.QtGui"] = mock_gui

# 2. Now import our tray component and standard dependencies
import pytest
from src.ui.tray import TranscriberTrayIcon

def test_tray_initialization():
    """Test standard initialization and setup of tray menu items."""
    mock_manager = MagicMock()
    mock_manager.state = "idle"
    mock_manager.config.get.side_effect = lambda key: {
        "api_key": "dummy-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "system_prompt": "transcribe"
    }[key]

    with patch("src.ui.tray.QPixmap"), patch("src.ui.tray.QPainter"):
        tray = TranscriberTrayIcon(manager=mock_manager)
        
        # Check initial state values
        assert tray._tooltip == "Transcriber - Ожидание"
        assert len(tray.menu._actions) == 6 # Status, separator, Toggle, Settings, separator, Exit
        
        # Verify status action details
        status_action = tray.menu._actions[0]
        assert status_action._text == "Статус: Ожидание"
        assert status_action._enabled == False
        
        # Verify toggle record action
        toggle_action = tray.menu._actions[2]
        assert toggle_action._text == "Начать запись"
        
        # Verify exit action
        exit_action = tray.menu._actions[5]
        assert exit_action._text == "Выход"

def test_tray_state_changed_signals():
    """Test that menu text and tray icons update gracefully on manager state changes."""
    mock_manager = MagicMock()
    mock_manager.state = "idle"
    mock_manager.config.get.side_effect = lambda key: {
        "api_key": "dummy",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "system_prompt": "transcribe"
    }[key]

    with patch("src.ui.tray.QPixmap"), patch("src.ui.tray.QPainter"):
        tray = TranscriberTrayIcon(manager=mock_manager)
        
        # Transition to recording
        tray.on_state_changed("recording")
        assert tray._tooltip == "Transcriber - Запись..."
        assert tray.status_action._text == "Статус: Идет запись..."
        assert tray.toggle_record_action._text == "Остановить запись"
        assert tray.toggle_record_action._enabled == True
        assert tray.settings_action._enabled == False
        
        # Transition to transcribing
        tray.on_state_changed("transcribing")
        assert tray._tooltip == "Transcriber - Распознавание..."
        assert tray.status_action._text == "Статус: Распознавание..."
        assert tray.toggle_record_action._text == "Распознавание..."
        assert tray.toggle_record_action._enabled == False
        
        # Transition back to idle
        tray.on_state_changed("idle")
        assert tray._tooltip == "Transcriber - Ожидание"
        assert tray.status_action._text == "Статус: Ожидание"
        assert tray.toggle_record_action._text == "Начать запись"
        assert tray.toggle_record_action._enabled == True
        assert tray.settings_action._enabled == True

def test_tray_notifications():
    """Test system notifications requested from managers."""
    mock_manager = MagicMock()
    mock_manager.state = "idle"
    
    with patch("src.ui.tray.QPixmap"), patch("src.ui.tray.QPainter"):
        tray = TranscriberTrayIcon(manager=mock_manager)
        
        tray.show_notification("Header text", "Message body")
        assert tray._notification == ("Header text", "Message body", "Information", 3000)

def test_tray_toggle_and_activation_toggles():
    """Test click activation and toggling behavior."""
    mock_manager = MagicMock()
    mock_manager.state = "idle"
    
    with patch("src.ui.tray.QPixmap"), patch("src.ui.tray.QPainter"):
        tray = TranscriberTrayIcon(manager=mock_manager)
        
        # Test double click triggers recording toggle (idle -> start)
        tray.on_tray_activated(2)
        mock_manager.start_recording.assert_called_once()
        
        # Change state to recording
        mock_manager.state = "recording"
        tray.on_tray_activated(3) # single click
        mock_manager.stop_recording.assert_called_once()

def test_lazy_loaded_settings_flow():
    """Test settings window lazy loading, caching and destruction reference cleanups."""
    mock_manager = MagicMock()
    mock_manager.state = "idle"
    mock_manager.config.get.side_effect = lambda key: {
        "api_key": "dummy",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "system_prompt": "transcribe"
    }[key]

    with patch("src.ui.tray.QPixmap"), \
         patch("src.ui.tray.QPainter"), \
         patch("src.ui.tray.SettingsDialog") as mock_settings_class:
         
        tray = TranscriberTrayIcon(manager=mock_manager)
        
        # Dialog shouldn't exist initially
        assert tray.settings_dialog is None
        
        # Trigger settings dialog lazy load
        tray.open_settings()
        assert tray.settings_dialog is not None
        mock_settings_class.assert_called_once_with(mock_manager.config)
        
        # Open settings again shouldn't re-create it
        tray.open_settings()
        mock_settings_class.assert_called_once() # still only called once
        
        # Clear dialog reference via destroyed signal
        tray._clear_settings_reference()
        assert tray.settings_dialog is None

def test_quit_app_triggers_shutdown():
    """Test that quit action cleanly shuts down the app manager."""
    mock_manager = MagicMock()
    
    with patch("src.ui.tray.QPixmap"), \
         patch("src.ui.tray.QPainter"), \
         patch("src.ui.tray.QApplication") as mock_qapp:
         
        tray = TranscriberTrayIcon(manager=mock_manager)
        tray.quit_app()
        
        mock_manager.shutdown.assert_called_once()
        mock_qapp.quit.assert_called_once()
