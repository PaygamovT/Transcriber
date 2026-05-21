import sys
import os
import logging
from PyQt6.QtWidgets import QApplication

from src.config import ConfigManager
from src.orchestrator.manager import AppManager
from src.ui.tray import TranscriberTrayIcon

def setup_global_logging():
    """Configures application-wide logging formats and levels."""
    log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    numeric_level = getattr(logging, log_level_env, logging.DEBUG)
    
    # Create standard formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
    )
    
    # Stream handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    logging.getLogger("transcriber").setLevel(numeric_level)
    
    logger = logging.getLogger("transcriber.main")
    logger.info(f"Logging initialized. Level: {log_level_env}")

def main():
    """Main entry point of the Transcriber tray application."""
    setup_global_logging()
    logger = logging.getLogger("transcriber.main")
    logger.info("Starting Transcriber Application Composition Root")
    
    try:
        # 1. Initialize QApplication
        logger.debug("Initializing QApplication")
        app = QApplication(sys.argv)
        
        # Ensure application remains alive in the tray even when settings window is closed
        logger.debug("Configuring quitOnLastWindowClosed to False")
        app.setQuitOnLastWindowClosed(False)
        
        # 2. Instantiate ConfigManager
        logger.debug("Initializing ConfigManager")
        config = ConfigManager()
        
        # 3. Instantiate Coordinator / Controller
        logger.debug("Initializing AppManager")
        manager = AppManager(config=config)
        
        # 4. Instantiate Tray Icon UI
        logger.debug("Initializing TranscriberTrayIcon")
        tray = TranscriberTrayIcon(manager=manager)
        tray.show()
        logger.info("TranscriberTrayIcon visible in system tray")
        
        # 5. Run event loop
        logger.info("Entering QApplication execution loop")
        exit_code = app.exec()
        logger.info(f"QApplication loop exited with code: {exit_code}")
        
        # Clean shutdown of background threads
        logger.debug("Performing final clean AppManager shutdown")
        manager.shutdown()
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Unhandled exception during startup sequence: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
