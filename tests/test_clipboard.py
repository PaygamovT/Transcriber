import pytest
from unittest.mock import MagicMock, patch
from src.services.clipboard import ClipboardService

def test_clipboard_copy_with_callback():
    """Test copying to clipboard using the injected callback."""
    mock_callback = MagicMock()
    service = ClipboardService(clipboard_setter_callback=mock_callback)
    
    service.copy_to_clipboard("hello world")
    
    mock_callback.assert_called_once_with("hello world")

def test_clipboard_copy_empty_text():
    """Test copying empty text is ignored."""
    mock_callback = MagicMock()
    service = ClipboardService(clipboard_setter_callback=mock_callback)
    
    service.copy_to_clipboard("")
    
    mock_callback.assert_not_called()

@patch("keyboard.write")
def test_typewriter_typing_emulation(mock_keyboard_write):
    """Test keyboard typewriter emulation typing logic using keyboard.write."""
    service = ClipboardService()
    
    service.type_text("test typing")
    
    mock_keyboard_write.assert_called_once_with("test typing", delay=0.01)

@patch("keyboard.write")
def test_typewriter_typing_empty_text(mock_keyboard_write):
    """Test that emulating empty typing is ignored and does not call keyboard.write."""
    service = ClipboardService()
    
    service.type_text("")
    
    mock_keyboard_write.assert_not_called()

def test_clipboard_copy_pyqt_fallback():
    """Test PyQt6 fallback copy behavior when no callback is provided."""
    import sys
    from unittest.mock import MagicMock
    
    # Create mock PyQt6 and submodules
    mock_pyqt6 = MagicMock()
    mock_widgets = MagicMock()
    mock_pyqt6.QtWidgets = mock_widgets
    
    mock_app = MagicMock()
    mock_widgets.QApplication.instance.return_value = mock_app
    mock_clipboard = MagicMock()
    mock_app.clipboard.return_value = mock_clipboard
    
    # Temporarily inject into sys.modules
    sys.modules["PyQt6"] = mock_pyqt6
    sys.modules["PyQt6.QtWidgets"] = mock_widgets
    
    try:
        service = ClipboardService(clipboard_setter_callback=None)
        service.copy_to_clipboard("pyqt text")
        
        mock_widgets.QApplication.instance.assert_called_once()
        mock_app.clipboard.assert_called_once()
        mock_clipboard.setText.assert_called_once_with("pyqt text")
    finally:
        # Clean up sys.modules
        sys.modules.pop("PyQt6", None)
        sys.modules.pop("PyQt6.QtWidgets", None)

