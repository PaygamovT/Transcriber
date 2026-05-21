import pytest
from unittest.mock import MagicMock, patch
from src.orchestrator.hotkey import HotkeyListener

def test_hotkey_listener_initialization():
    """Test hotkey listener initialization."""
    mock_callback = MagicMock()
    listener = HotkeyListener(hotkey_str="<ctrl>+<shift>+space", callback=mock_callback)
    
    assert listener.hotkey_str == "<ctrl>+<shift>+<space>"
    assert listener.callback == mock_callback
    assert listener.listener is None

@patch("src.orchestrator.hotkey.keyboard.GlobalHotKeys")
def test_hotkey_listener_lifecycle(mock_global_hotkeys_class):
    """Test start, stop, and trigger lifecycle."""
    mock_listener = MagicMock()
    mock_global_hotkeys_class.return_value = mock_listener
    
    mock_callback = MagicMock()
    listener = HotkeyListener(hotkey_str="<ctrl>+<shift>+space", callback=mock_callback)
    
    # 1. Start
    listener.start()
    
    assert listener.listener == mock_listener
    mock_global_hotkeys_class.assert_called_once()
    mock_listener.start.assert_called_once()
    
    # Check that it instantiated GlobalHotKeys with the correct hotkey dict mapping to _on_triggered
    hotkeys_dict = mock_global_hotkeys_class.call_args[0][0]
    assert "<ctrl>+<shift>+<space>" in hotkeys_dict
    
    # 2. Trigger the callback through the internal trigger method
    listener._on_triggered()
    mock_callback.assert_called_once()
    
    # 3. Stop
    listener.stop()
    assert listener.listener is None
    mock_listener.stop.assert_called_once()
