import sys
from unittest.mock import MagicMock, patch

# 1. Create and inject mock PyQt6 modules before importing managers to avoid ModuleNotFoundError
class MockSignal:
    def __init__(self, *types):
        self.callbacks = []
    def connect(self, callback):
        self.callbacks.append(callback)
    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)

class MockQObject:
    def __init__(self, *args, **kwargs):
        pass

class MockQThread(MockQObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.finished = MockSignal()
        self.error = MockSignal()
    def start(self):
        # Run synchronously during testing for predictability
        self.run()
    def isRunning(self):
        return False
    def terminate(self):
        pass
    def wait(self):
        pass

class MockQTimer(MockQObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = MockSignal()
        self._active = False
    def start(self, ms):
        self._active = True
    def stop(self):
        self._active = False
    def setSingleShot(self, val):
        pass
    def isActive(self):
        return self._active

mock_pyqt6 = MagicMock()
mock_core = MagicMock()
mock_widgets = MagicMock()

mock_pyqt6.QtCore = mock_core
mock_pyqt6.QtWidgets = mock_widgets

mock_core.pyqtSignal = MockSignal
mock_core.QObject = MockQObject
mock_core.QThread = MockQThread
mock_core.QTimer = MockQTimer

sys.modules["PyQt6"] = mock_pyqt6
sys.modules["PyQt6.QtCore"] = mock_core
sys.modules["PyQt6.QtWidgets"] = mock_widgets

# 2. Now import our actual manager components
import pytest
from src.orchestrator.manager import AppManager, TranscriptionWorker

def test_app_manager_initialization(tmp_path):
    """Test standard manager setup and state initialization."""
    # Mock config
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "api_key": "test-api-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "test-prompt"
    }[key]
    
    mock_recorder = MagicMock()
    mock_clipboard = MagicMock()
    
    # Patch HotkeyListener to avoid background pynput threads during test
    with patch("src.orchestrator.manager.HotkeyListener") as mock_hotkey_class:
        manager = AppManager(
            config=mock_config,
            recorder=mock_recorder,
            clipboard=mock_clipboard
        )
        
        assert manager.state == "idle"
        assert manager.recorder == mock_recorder
        assert manager.clipboard == mock_clipboard
        assert manager.transcription_service.api_key == "test-api-key"
        assert manager.transcription_service.model == "google/gemini-3.1-flash-lite"
        
        mock_hotkey_class.assert_called_once()
        assert manager.hotkey_listener is not None

def test_recording_start_and_stop(tmp_path):
    """Test start_recording and stop_recording transitions and calls."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "api_key": "test-api-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "clean",
        "system_prompt": "test-prompt"
    }[key]
    
    mock_recorder = MagicMock()
    mock_clipboard = MagicMock()
    
    with patch("src.orchestrator.manager.HotkeyListener"):
        manager = AppManager(
            config=mock_config,
            recorder=mock_recorder,
            clipboard=mock_clipboard
        )
        
        # 1. Start Recording
        state_changes = []
        manager.state_changed.connect(state_changes.append)
        
        manager.start_recording()
        
        assert manager.state == "recording"
        assert len(state_changes) == 1
        assert state_changes[0] == "recording"
        mock_recorder.start_recording.assert_called_once()
        assert manager.limit_timer.isActive()
        
        # 2. Stop Recording
        mock_recorder.stop_recording.return_value = b"wav audio bytes"
        
        # Mock TranscriptionWorker background thread starting
        with patch("src.orchestrator.manager.TranscriptionWorker") as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker
            
            manager.stop_recording()
            
            assert manager.state == "transcribing"
            assert state_changes[1] == "transcribing"
            assert not manager.limit_timer.isActive()
            mock_recorder.stop_recording.assert_called_once()
            
            # Verify worker initialization
            mock_worker_class.assert_called_once_with(manager.transcription_service, b"wav audio bytes", mode="clean")
            mock_worker.start.assert_called_once()

def test_hotkey_toggle_behavior(tmp_path):
    """Test that the internal hotkey trigger toggles between start and stop."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "api_key": "test-api-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "test-prompt"
    }[key]
    
    mock_recorder = MagicMock()
    mock_clipboard = MagicMock()
    
    with patch("src.orchestrator.manager.HotkeyListener"):
        manager = AppManager(
            config=mock_config,
            recorder=mock_recorder,
            clipboard=mock_clipboard
        )
        
        # Trigger 1 (idle -> starts recording)
        with patch.object(manager, "start_recording") as mock_start:
            manager._handle_hotkey_trigger()
            mock_start.assert_called_once()
            
        # Trigger 2 (recording -> stops recording)
        manager.state = "recording"
        with patch.object(manager, "stop_recording") as mock_stop:
            manager._handle_hotkey_trigger()
            mock_stop.assert_called_once()

def test_transcription_success_handling_clipboard(tmp_path):
    """Test handling of successful transcription in clipboard mode."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "api_key": "test-api-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "test-prompt"
    }[key]
    
    mock_recorder = MagicMock()
    mock_clipboard = MagicMock()
    
    with patch("src.orchestrator.manager.HotkeyListener"):
        manager = AppManager(config=mock_config, recorder=mock_recorder, clipboard=mock_clipboard)
        manager.state = "transcribing"
        
        notifications = []
        manager.notification_requested.connect(lambda title, msg: notifications.append((title, msg)))
        
        manager._handle_transcription_success("hello world transcribed")
        
        assert manager.state == "idle"
        mock_clipboard.copy_to_clipboard.assert_called_once_with("hello world transcribed")
        mock_clipboard.type_text.assert_not_called()
        assert len(notifications) == 1
        assert "скопирован" in notifications[0][1]

def test_transcription_success_handling_typewriter(tmp_path):
    """Test handling of successful transcription in typewriter mode."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "api_key": "test-api-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "typewriter",
        "transcription_mode": "normal",
        "system_prompt": "test-prompt"
    }[key]
    
    mock_recorder = MagicMock()
    mock_clipboard = MagicMock()
    
    with patch("src.orchestrator.manager.HotkeyListener"):
        manager = AppManager(config=mock_config, recorder=mock_recorder, clipboard=mock_clipboard)
        manager.state = "transcribing"
        
        manager._handle_transcription_success("typed text")
        
        assert manager.state == "idle"
        mock_clipboard.type_text.assert_called_once_with("typed text")
        mock_clipboard.copy_to_clipboard.assert_not_called()

def test_transcription_error_handling(tmp_path):
    """Test error handling from the background worker."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key: {
        "api_key": "test-api-key",
        "model": "google/gemini-3.1-flash-lite",
        "hotkey": "<ctrl>+<shift>+space",
        "audio_duration_limit": 30,
        "insert_mode": "clipboard",
        "transcription_mode": "normal",
        "system_prompt": "test-prompt"
    }[key]
    
    mock_recorder = MagicMock()
    mock_clipboard = MagicMock()
    
    with patch("src.orchestrator.manager.HotkeyListener"):
        manager = AppManager(config=mock_config, recorder=mock_recorder, clipboard=mock_clipboard)
        manager.state = "transcribing"
        
        notifications = []
        manager.notification_requested.connect(lambda title, msg: notifications.append((title, msg)))
        
        manager._handle_transcription_error("Connection timed out")
        
        assert manager.state == "idle"
        assert len(notifications) == 1
        assert notifications[0][0] == "Ошибка транскрипции"
        assert "Connection timed out" in notifications[0][1]

def test_transcription_worker_passes_mode():
    """Test that TranscriptionWorker initializes and passes the mode parameter to the service."""
    mock_service = MagicMock()
    wav_bytes = b"test raw wav bytes"
    
    # Test worker with default mode
    worker_default = TranscriptionWorker(mock_service, wav_bytes)
    assert worker_default.mode == "normal"
    worker_default.run()
    mock_service.transcribe.assert_called_once_with(wav_bytes, "normal")
    
    # Test worker with custom mode
    mock_service.reset_mock()
    worker_clean = TranscriptionWorker(mock_service, wav_bytes, mode="clean")
    assert worker_clean.mode == "clean"
    worker_clean.run()
    mock_service.transcribe.assert_called_once_with(wav_bytes, "clean")
