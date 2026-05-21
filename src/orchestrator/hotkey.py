import logging
import os
from pynput import keyboard
from typing import Callable, Optional

# Setup logging
logger = logging.getLogger("transcriber.hotkey")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class HotkeyListener:
    """Listens globally for a configured hotkey and invokes a callback when triggered."""
    
    def __init__(self, hotkey_str: str, callback: Callable[[], None]):
        logger.debug("HotkeyListener.__init__ entering")
        self.callback = callback
        self.listener: Optional[keyboard.GlobalHotKeys] = None
        
        # Normalize common user mistakes in hotkeys
        # pynput expects special keys to be in angle brackets like <space>, <ctrl>, <shift>, etc.
        raw_str = hotkey_str.lower().strip()
        parts = raw_str.split('+')
        for i, part in enumerate(parts):
            part_stripped = part.strip()
            if part_stripped == "space":
                parts[i] = "<space>"
            elif part_stripped == "ctrl" or part_stripped == "control":
                parts[i] = "<ctrl>"
            elif part_stripped == "shift":
                parts[i] = "<shift>"
            elif part_stripped == "alt":
                parts[i] = "<alt>"
            elif part_stripped in ("cmd", "win", "win_l", "win_r", "command", "super"):
                parts[i] = "<cmd>"
            elif part_stripped.startswith("<") and part_stripped.endswith(">"):
                parts[i] = part_stripped
            elif len(part_stripped) > 1:
                # E.g. enter, tab, esc, backspace
                parts[i] = f"<{part_stripped}>"
            else:
                parts[i] = part_stripped
                
        self.hotkey_str = "+".join(parts)
        logger.debug(f"HotkeyListener initialized with normalized hotkey '{self.hotkey_str}' (raw: '{hotkey_str}')")
        logger.debug("HotkeyListener.__init__ exiting successfully")

    def start(self) -> None:
        """Starts the global hotkey listener in a background thread."""
        logger.debug("HotkeyListener.start entering")
        if self.listener is not None:
            logger.warning("Listener is already running")
            return
            
        try:
            logger.info(f"Starting global hotkey listener for: {self.hotkey_str}")
            # GlobalHotKeys takes a dict mapping hotkey combination to callback
            self.listener = keyboard.GlobalHotKeys({
                self.hotkey_str: self._on_triggered
            })
            self.listener.start()
            logger.info("Global hotkey listener successfully started in background")
        except Exception as e:
            self.listener = None
            logger.error(f"Failed to start global hotkey listener: {e}", exc_info=True)
            raise
            
        logger.debug("HotkeyListener.start exiting")

    def stop(self) -> None:
        """Stops the global hotkey listener."""
        logger.debug("HotkeyListener.stop entering")
        if self.listener is None:
            logger.warning("Listener was not running")
            return
            
        try:
            logger.debug("Stopping pynput global hotkey listener")
            self.listener.stop()
            logger.info("Global hotkey listener successfully stopped")
        except Exception as e:
            logger.error(f"Error while stopping global hotkey listener: {e}", exc_info=True)
        finally:
            self.listener = None
            
        logger.debug("HotkeyListener.stop exiting")

    def _on_triggered(self) -> None:
        """Internal callback invoked when the hotkey is triggered by pynput."""
        logger.info(f"Hotkey '{self.hotkey_str}' triggered globally!")
        try:
            self.callback()
            logger.debug("Hotkey callback successfully invoked")
        except Exception as e:
            logger.error(f"Error executing callback for hotkey '{self.hotkey_str}': {e}", exc_info=True)
