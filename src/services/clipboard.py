import logging
import os
from pynput.keyboard import Controller
from typing import Callable, Optional

# Setup logging
logger = logging.getLogger("transcriber.clipboard")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class ClipboardService:
    """Service to handle clipboard injection and keyboard typing emulation."""
    
    def __init__(self, clipboard_setter_callback: Optional[Callable[[str], None]] = None):
        """Initializes the service.
        
        Args:
            clipboard_setter_callback: Optional callback to set system clipboard.
                                        Allows decoupling the service from PyQt6.
        """
        logger.debug("ClipboardService.__init__ entering")
        try:
            self.keyboard = Controller()
            logger.debug("pynput keyboard Controller initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pynput keyboard Controller: {e}", exc_info=True)
            self.keyboard = None
            
        self.clipboard_setter_callback = clipboard_setter_callback
        logger.debug("ClipboardService.__init__ exiting successfully")

    def copy_to_clipboard(self, text: str) -> None:
        """Copies the given text to the system clipboard.
        
        Args:
            text: The text to copy.
        """
        logger.debug("ClipboardService.copy_to_clipboard entering")
        if not text:
            logger.warning("Empty text, ignoring clipboard copy")
            return
            
        logger.info(f"Copying text to clipboard ({len(text)} characters)")
        if self.clipboard_setter_callback:
            try:
                self.clipboard_setter_callback(text)
                logger.debug("Clipboard setter callback successfully executed")
            except Exception as e:
                logger.error(f"Failed to execute clipboard setter callback: {e}", exc_info=True)
                raise
        else:
            # Fallback to direct use of PyQt6 inside the method if no callback was provided.
            # This maintains standalone usage without requiring a callback, while keeping
            # top-level imports clean.
            try:
                logger.debug("Attempting to use PyQt6 QApplication clipboard fallback")
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    clipboard = app.clipboard()
                    clipboard.setText(text)
                    logger.debug("Successfully copied to clipboard using PyQt6 QApplication clipboard")
                else:
                    logger.error("No active QApplication instance found for clipboard copy")
                    raise RuntimeError("No active QApplication instance and no clipboard callback provided.")
            except ImportError as e:
                logger.error(f"PyQt6 not available for clipboard fallback: {e}")
                raise RuntimeError("PyQt6 is not installed and no clipboard callback was provided.") from e
                
        logger.debug("ClipboardService.copy_to_clipboard exiting")

    def type_text(self, text: str) -> None:
        """Emulates keystrokes to type the given text at the current cursor.
        
        Args:
            text: The text to type.
        """
        logger.debug("ClipboardService.type_text entering")
        if not text:
            logger.warning("Empty text, ignoring typing emulation")
            return
            
        logger.info(f"Emulating keyboard typing for '{text[:20]}...' ({len(text)} characters) using keyboard.write")
        try:
            import keyboard
            # Use keyboard.write for proper Unicode (Russian/Uzbek/English) support
            keyboard.write(text, delay=0.01)
            logger.info("Successfully completed keyboard typing emulation using keyboard.write")
        except Exception as e:
            logger.error(f"Failed keyboard typing emulation using keyboard.write: {e}", exc_info=True)
            raise
            
        logger.debug("ClipboardService.type_text exiting")
