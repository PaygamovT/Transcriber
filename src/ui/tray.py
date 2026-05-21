import logging
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PyQt6.QtCore import QObject, pyqtSlot, Qt

from src.orchestrator.manager import AppManager
from src.ui.settings import SettingsDialog

# Setup logging
logger = logging.getLogger("transcriber.tray")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class TranscriberTrayIcon(QSystemTrayIcon):
    """Sleek PyQt6 system tray icon for Transcriber with custom visual state indicators and QSS menu."""

    def __init__(self, manager: AppManager, parent=None):
        super().__init__(parent)
        logger.debug("TranscriberTrayIcon.__init__ entering")
        self.manager = manager
        self.settings_dialog = None
        
        # Connect to manager signals
        self.manager.state_changed.connect(self.on_state_changed)
        self.manager.notification_requested.connect(self.show_notification)
        
        # Build tray UI
        self.setup_icon()
        self.setup_menu()
        
        # Handle double click on the tray icon to toggle recording (or open settings)
        self.activated.connect(self.on_tray_activated)
        
        logger.debug("TranscriberTrayIcon.__init__ exiting successfully")

    def _create_pixmap_icon(self, color_hex: str, draw_inner: bool = False) -> QIcon:
        """Helper to dynamically generate high-DPI state indicator icon with QPainter."""
        logger.debug(f"Creating pixmap icon for color: {color_hex}, inner ring: {draw_inner}")
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Outer border / glow effect
        painter.setBrush(QColor("#29292E"))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawEllipse(2, 2, 28, 28)
        
        # Central colored circle
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.PenStyle.NoPen if not draw_inner else QColor("#FFFFFF"))
        painter.drawEllipse(6, 6, 20, 20)
        
        if draw_inner:
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(12, 12, 8, 8)
            
        painter.end()
        return QIcon(pixmap)

    def setup_icon(self):
        """Initializes state icon cache and sets the default idle icon."""
        logger.debug("TranscriberTrayIcon.setup_icon entering")
        from PyQt6.QtCore import Qt  # ensure imported inside for dynamic mocking safely if needed
        self.icon_idle = self._create_pixmap_icon("#8F2DFF")       # Deep premium purple
        self.icon_recording = self._create_pixmap_icon("#FF3B30")  # Vibrant red
        self.icon_transcribing = self._create_pixmap_icon("#007AFF", draw_inner=True) # Pulsating blue
        
        # Set default
        self.setIcon(self.icon_idle)
        self.setToolTip("Transcriber - Ожидание")
        logger.debug("TranscriberTrayIcon.setup_icon exiting")

    def setup_menu(self):
        """Builds a beautiful premium context menu styled with QSS."""
        logger.debug("TranscriberTrayIcon.setup_menu entering")
        self.menu = QMenu()
        
        # Apply dark mode sleek styling
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #121214;
                color: #C4C4CC;
                border: 1px solid #202024;
                border-radius: 8px;
                padding: 4px 0px;
                font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 8px 24px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #1A1A1E;
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                color: #4C4C54;
            }
            QMenu::separator {
                height: 1px;
                background-color: #202024;
                margin: 6px 0px;
            }
        """)
        
        # 1. State / Status Header (Disabled action for visual status)
        self.status_action = QAction("Статус: Ожидание", self)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()
        
        # 2. Toggle Record Action
        self.toggle_record_action = QAction("Начать запись", self)
        self.toggle_record_action.triggered.connect(self.toggle_recording)
        self.menu.addAction(self.toggle_record_action)
        
        # 3. Settings Action
        self.settings_action = QAction("Настройки...", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(self.settings_action)
        
        self.menu.addSeparator()
        
        # 4. Quit Action
        self.quit_action = QAction("Выход", self)
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)
        
        self.setContextMenu(self.menu)
        logger.debug("TranscriberTrayIcon.setup_menu exiting")

    @pyqtSlot(str)
    def on_state_changed(self, state: str):
        """Fires on AppManager state updates to dynamically adjust tooltip, icon and menu items."""
        logger.debug(f"TranscriberTrayIcon.on_state_changed triggered with state: {state}")
        
        if state == "recording":
            self.setIcon(self.icon_recording)
            self.setToolTip("Transcriber - Запись...")
            self.status_action.setText("Статус: Идет запись...")
            self.toggle_record_action.setText("Остановить запись")
            self.toggle_record_action.setEnabled(True)
            self.settings_action.setEnabled(False)
        elif state == "transcribing":
            self.setIcon(self.icon_transcribing)
            self.setToolTip("Transcriber - Распознавание...")
            self.status_action.setText("Статус: Распознавание...")
            self.toggle_record_action.setText("Распознавание...")
            self.toggle_record_action.setEnabled(False)
            self.settings_action.setEnabled(False)
        else:  # idle
            self.setIcon(self.icon_idle)
            self.setToolTip("Transcriber - Ожидание")
            self.status_action.setText("Статус: Ожидание")
            self.toggle_record_action.setText("Начать запись")
            self.toggle_record_action.setEnabled(True)
            self.settings_action.setEnabled(True)
            
        logger.debug("TranscriberTrayIcon.on_state_changed exiting successfully")

    @pyqtSlot(str, str)
    def show_notification(self, title: str, message: str):
        """Displays native OS notification from system tray icon."""
        logger.debug(f"TranscriberTrayIcon showing notification: {title} | {message}")
        self.showMessage(
            title, 
            message, 
            QSystemTrayIcon.MessageIcon.Information, 
            3000
        )

    def on_tray_activated(self, reason):
        """Toggles recording on double click, or opens settings depending on activation reason."""
        logger.debug(f"TranscriberTrayIcon activated. Reason code: {reason}")
        # QSystemTrayIcon.ActivationReason: DoubleClick is 2, Trigger (Single Click) is 3
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            logger.info("Tray clicked/double-clicked. Toggling recording state.")
            self.toggle_recording()

    def toggle_recording(self):
        """Starts or stops recording via manager depending on current state."""
        logger.debug("TranscriberTrayIcon.toggle_recording entering")
        if self.manager.state == "idle":
            self.manager.start_recording()
        elif self.manager.state == "recording":
            self.manager.stop_recording()
        else:
            logger.warning(f"Cannot toggle recording while in state: {self.manager.state}")

    def open_settings(self):
        """Lazy instantiates and opens the Settings dialog window."""
        logger.debug("TranscriberTrayIcon.open_settings entering")
        if self.settings_dialog is not None:
            logger.debug("Settings dialog already exists. Bringing to front.")
            self.settings_dialog.activateWindow()
            self.settings_dialog.raise_()
            return
            
        logger.info("Instantiating lazy SettingsDialog")
        self.settings_dialog = SettingsDialog(self.manager.config)
        self.settings_dialog.accepted.connect(self.manager.reload_configuration)
        self.settings_dialog.destroyed.connect(self._clear_settings_reference)
        
        self.settings_dialog.show()
        self.settings_dialog.activateWindow()
        self.settings_dialog.raise_()
        logger.debug("TranscriberTrayIcon.open_settings exiting successfully")

    def _clear_settings_reference(self):
        """Slot connected to QObject destroyed signal to clear dialog reference and free RAM."""
        logger.debug("SettingsDialog destroyed signal received. Clearing local reference.")
        self.settings_dialog = None

    def quit_app(self):
        """Triggers clean manager shutdown and exits PyQt6 QApplication."""
        logger.info("Exit clicked. Starting shutdown sequence.")
        self.manager.shutdown()
        QApplication.quit()
        logger.debug("TranscriberTrayIcon.quit_app completed")
