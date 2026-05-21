import logging
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QSpinBox, QComboBox, QPushButton, QFormLayout,
    QGroupBox, QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt
from src.config import ConfigManager

# Setup logging
logger = logging.getLogger("transcriber.settings")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class SettingsDialog(QDialog):
    """Ultra-premium configuration dialog with a tabbed layout and modern aesthetics."""
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        logger.debug("SettingsDialog.__init__ entering")
        self.config = config
        
        self.provider_presets = {
            "openrouter": [
                "google/gemini-3.1-flash-lite",
                "openai/whisper-large-v3",
                "meta-llama/llama-3-70b-instruct"
            ],
            "openai": [
                "whisper-1"
            ],
            "groq": [
                "whisper-large-v3",
                "whisper-large-v3-turbo",
                "distil-whisper-large-v3-en"
            ]
        }
        
        self.temp_settings = {
            "openrouter": {
                "api_key": self.config.get("openrouter_api_key"),
                "model": self.config.get("openrouter_model")
            },
            "openai": {
                "api_key": self.config.get("openai_api_key"),
                "model": self.config.get("openai_model")
            },
            "groq": {
                "api_key": self.config.get("groq_api_key"),
                "model": self.config.get("groq_model")
            }
        }
        
        self.current_provider = "openrouter"
        
        self.setWindowTitle("Настройки Transcriber")
        self.setMinimumSize(540, 480)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.setup_ui()
        self.load_settings()
        self.apply_theme()
        
        logger.debug("SettingsDialog.__init__ exiting successfully")

    def setup_ui(self):
        logger.debug("SettingsDialog.setup_ui entering")
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)
        
        # 1. Header with Gear/Sparkle Icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        header_icon = QLabel("⚙️")
        header_icon.setObjectName("HeaderIcon")
        header_title = QLabel("Transcriber Settings")
        header_title.setObjectName("HeaderLabel")
        
        header_layout.addWidget(header_icon)
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # 2. Navigation Tabs Bar
        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(16)
        tab_layout.setContentsMargins(0, 0, 0, 4)
        
        self.api_tab_btn = QPushButton("❖  API Settings")
        self.api_tab_btn.setObjectName("ActiveTab")
        self.api_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.api_tab_btn.clicked.connect(lambda: self.set_active_tab(0))
        
        self.rec_tab_btn = QPushButton("🎙️  Recording & Playback")
        self.rec_tab_btn.setObjectName("InactiveTab")
        self.rec_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rec_tab_btn.clicked.connect(lambda: self.set_active_tab(1))
        
        tab_layout.addWidget(self.api_tab_btn)
        tab_layout.addWidget(self.rec_tab_btn)
        tab_layout.addStretch()
        
        main_layout.addLayout(tab_layout)
        
        # 3. Stacked Content Widget inside nested container
        self.content_card = QGroupBox()
        self.content_card.setObjectName("ContentCard")
        
        card_layout = QVBoxLayout(self.content_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(0)
        
        self.stacked_widget = QStackedWidget()
        card_layout.addWidget(self.stacked_widget)
        
        # --- Page 1: API Settings ---
        self.page_api = QWidget()
        page_api_layout = QFormLayout(self.page_api)
        page_api_layout.setContentsMargins(0, 0, 0, 0)
        page_api_layout.setSpacing(16)
        page_api_layout.setVerticalSpacing(18)
        
        # API Provider Combobox
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("OpenRouter", "openrouter")
        self.provider_combo.addItem("OpenAI", "openai")
        self.provider_combo.addItem("Groq", "groq")
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        page_api_layout.addRow(QLabel("API Provider"), self.provider_combo)
        
        # API Key (with inline visibility toggle button)
        self.api_key_label = QLabel("API Key OpenRouter")
        
        api_key_container = QWidget()
        api_key_container.setObjectName("ApiKeyContainer")
        key_layout = QHBoxLayout(api_key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(4)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setObjectName("ApiKeyInput")
        
        self.toggle_visibility_btn = QPushButton("👁️")
        self.toggle_visibility_btn.setObjectName("VisibilityButton")
        self.toggle_visibility_btn.setFixedWidth(36)
        self.toggle_visibility_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_visibility_btn.clicked.connect(self.toggle_password_visibility)
        
        key_layout.addWidget(self.api_key_input)
        key_layout.addWidget(self.toggle_visibility_btn)
        
        page_api_layout.addRow(self.api_key_label, api_key_container)
        
        # Transcription Model
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setObjectName("ModelInput")
        page_api_layout.addRow(QLabel("Transcription Model"), self.model_combo)
        
        self.stacked_widget.addWidget(self.page_api)
        
        # --- Page 2: Recording & Playback ---
        self.page_rec = QWidget()
        page_rec_layout = QFormLayout(self.page_rec)
        page_rec_layout.setContentsMargins(0, 0, 0, 0)
        page_rec_layout.setSpacing(16)
        page_rec_layout.setVerticalSpacing(18)
        
        # Hotkey
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("<ctrl>+<shift>+space")
        page_rec_layout.addRow(QLabel("Global Hotkey"), self.hotkey_input)
        
        # Safety duration limit
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 300)
        self.duration_spin.setSuffix(" сек")
        page_rec_layout.addRow(QLabel("Recording Limit"), self.duration_spin)
        
        # Text Insert Mode
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Печатать на курсоре (Typewriter)", "typewriter")
        self.mode_combo.addItem("Копировать в буфер (Clipboard)", "clipboard")
        page_rec_layout.addRow(QLabel("Text Insertion Mode"), self.mode_combo)
        
        # Transcription Mode
        self.transcription_mode_combo = QComboBox()
        self.transcription_mode_combo.addItem("Обычная транскрипция (Normal)", "normal")
        self.transcription_mode_combo.addItem("Очистка от повторов и пауз (Clean)", "clean")
        self.transcription_mode_combo.addItem("Очистка + Перевод на английский (Translate)", "translate")
        page_rec_layout.addRow(QLabel("Transcription Mode"), self.transcription_mode_combo)
        
        # System Prompt
        self.prompt_input = QTextEdit()
        self.prompt_input.setTabChangesFocus(True)
        self.prompt_input.setMaximumHeight(80)
        page_rec_layout.addRow(QLabel("AI System Prompt"), self.prompt_input)
        
        self.stacked_widget.addWidget(self.page_rec)
        
        main_layout.addWidget(self.content_card)
        
        # 4. Action Buttons Layout (Cancel / Save)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setObjectName("CancelButton")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)
        
        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("SaveButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_settings)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        main_layout.addLayout(button_layout)
        
        logger.debug("SettingsDialog.setup_ui exiting")

    def set_active_tab(self, tab_index):
        """Switches the active stack page and updates tab styles dynamically."""
        logger.debug(f"SettingsDialog.set_active_tab: {tab_index}")
        self.stacked_widget.setCurrentIndex(tab_index)
        
        if tab_index == 0:
            self.api_tab_btn.setObjectName("ActiveTab")
            self.rec_tab_btn.setObjectName("InactiveTab")
        else:
            self.api_tab_btn.setObjectName("InactiveTab")
            self.rec_tab_btn.setObjectName("ActiveTab")
            
        # Re-apply stylesheets to refresh widget styles instantly
        self.api_tab_btn.style().polish(self.api_tab_btn)
        self.rec_tab_btn.style().polish(self.rec_tab_btn)

    def toggle_password_visibility(self):
        """Toggles the visibility of the API Key password characters."""
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_visibility_btn.setText("🙈")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_visibility_btn.setText("👁️")

    def on_provider_changed(self):
        logger.debug("SettingsDialog.on_provider_changed entering")
        new_provider = self.provider_combo.currentData()
        
        # Save current input values to previous provider's temp settings
        old_provider = getattr(self, "current_provider", None)
        if old_provider:
            self.temp_settings[old_provider]["api_key"] = self.api_key_input.text().strip()
            self.temp_settings[old_provider]["model"] = self.model_combo.currentText().strip()
            
        # Update current provider
        self.current_provider = new_provider
        
        # Update API key label and placeholder
        provider_names = {"openrouter": "OpenRouter", "openai": "OpenAI", "groq": "Groq"}
        p_name = provider_names.get(new_provider, "API")
        self.api_key_label.setText(f"API Key {p_name}")
        self.api_key_input.setPlaceholderText("Enter your API Key...")
        
        # Load values from temp settings for the new provider
        self.api_key_input.setText(self.temp_settings[new_provider]["api_key"])
        
        # Update model combo presets
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(self.provider_presets.get(new_provider, []))
        self.model_combo.blockSignals(False)
        
        # Match model text
        model_val = self.temp_settings[new_provider]["model"]
        idx = self.model_combo.findText(model_val)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setEditText(model_val)
            
        logger.debug("SettingsDialog.on_provider_changed exiting")

    def load_settings(self):
        logger.debug("SettingsDialog.load_settings entering")
        
        self.provider_combo.blockSignals(True)
        provider = self.config.get("provider") or "openrouter"
        self.current_provider = provider
        
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.blockSignals(False)
        
        # Initialize temp settings with latest persistent data from config
        self.temp_settings["openrouter"]["api_key"] = self.config.get("openrouter_api_key")
        self.temp_settings["openrouter"]["model"] = self.config.get("openrouter_model")
        self.temp_settings["openai"]["api_key"] = self.config.get("openai_api_key")
        self.temp_settings["openai"]["model"] = self.config.get("openai_model")
        self.temp_settings["groq"]["api_key"] = self.config.get("groq_api_key")
        self.temp_settings["groq"]["model"] = self.config.get("groq_model")
        
        # Trigger dynamic update
        self.on_provider_changed()
        
        # Load general configs
        self.hotkey_input.setText(self.config.get("hotkey"))
        self.duration_spin.setValue(self.config.get("audio_duration_limit"))
        
        # Match insert_mode data
        mode = self.config.get("insert_mode")
        idx = self.mode_combo.findData(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
            
        # Match transcription_mode data
        trans_mode = self.config.get("transcription_mode")
        idx = self.transcription_mode_combo.findData(trans_mode)
        if idx >= 0:
            self.transcription_mode_combo.setCurrentIndex(idx)
            
        self.prompt_input.setPlainText(self.config.get("system_prompt"))
        logger.debug("SettingsDialog.load_settings exiting")

    def save_settings(self):
        logger.debug("SettingsDialog.save_settings entering")
        
        # Save current input values to active provider's temp settings
        active_provider = self.provider_combo.currentData()
        self.temp_settings[active_provider]["api_key"] = self.api_key_input.text().strip()
        self.temp_settings[active_provider]["model"] = self.model_combo.currentText().strip()
        
        hotkey = self.hotkey_input.text().strip()
        duration = self.duration_spin.value()
        insert_mode = self.mode_combo.currentData()
        transcription_mode = self.transcription_mode_combo.currentData()
        prompt = self.prompt_input.toPlainText().strip()
        
        logger.info("Saving settings from configuration dialog UI")
        
        # First write individual provider details to the config dictionary
        for provider, settings in self.temp_settings.items():
            self.config.set(f"{provider}_api_key", settings["api_key"])
            self.config.set(f"{provider}_model", settings["model"])
            
        # Next, set the active provider
        self.config.set("provider", active_provider)
        
        # Save general fields
        self.config.set("hotkey", hotkey)
        self.config.set("audio_duration_limit", duration)
        self.config.set("insert_mode", insert_mode)
        self.config.set("transcription_mode", transcription_mode)
        self.config.set("system_prompt", prompt)
        
        logger.debug("SettingsDialog.save_settings exiting with accept")
        self.accept()

    def apply_theme(self):
        """Applies a high-fidelity, sketch-perfect dark QSS theme with rounded margins and gradients."""
        logger.debug("SettingsDialog.apply_theme entering")
        qss = """
            QDialog {
                background-color: #0D0F12;
                font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
            }
            
            /* Window Title/Header Styling */
            #HeaderIcon {
                font-size: 20px;
                color: #C084FC;
            }
            #HeaderLabel {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: 700;
            }
            
            /* Tabs Navigation */
            QPushButton#ActiveTab {
                background-color: transparent;
                border: none;
                color: #C084FC;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 4px;
                border-bottom: 2px solid #C084FC;
            }
            QPushButton#InactiveTab {
                background-color: transparent;
                border: none;
                color: #8C8E98;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 4px;
            }
            QPushButton#InactiveTab:hover {
                color: #C4C4CC;
            }
            
            /* Nested Card Layout */
            #ContentCard {
                border: 1px solid #1E202A;
                border-radius: 8px;
                background-color: #1A1C23;
                margin-top: 10px;
            }
            
            /* Form Labels */
            QLabel {
                color: #C4C4CC;
                font-size: 13px;
                font-weight: 500;
            }
            
            /* Inputs and Fields */
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #15171C;
                border: 1px solid #232631;
                border-radius: 6px;
                padding: 8px 12px;
                color: #E1E1E6;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #C084FC;
                background-color: #191B22;
            }
            
            /* API Key Layout Inner Container */
            #ApiKeyContainer {
                background: transparent;
                border: none;
            }
            
            /* Password Visibility Button */
            #VisibilityButton {
                background-color: #15171C;
                border: 1px solid #232631;
                border-radius: 6px;
                color: #A8A8B3;
                font-size: 14px;
                padding: 4px;
            }
            #VisibilityButton:hover {
                background-color: #191B22;
                border: 1px solid #C084FC;
                color: #FFFFFF;
            }
            
            /* Custom dropdown styling */
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #8C8E98;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #C084FC;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1C23;
                border: 1px solid #232631;
                selection-background-color: #C084FC;
                selection-color: #FFFFFF;
                color: #E1E1E6;
            }
            
            /* Bottom Action Buttons */
            QPushButton {
                font-size: 13px;
                font-weight: 600;
                border-radius: 6px;
                padding: 10px 20px;
            }
            
            #SaveButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #A855F7, stop:1 #7C3AED);
                color: #FFFFFF;
                border: none;
            }
            #SaveButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #C084FC, stop:1 #8B5CF6);
            }
            #SaveButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333EA, stop:1 #6D28D9);
            }
            
            #CancelButton {
                background-color: transparent;
                border: 1px solid #232631;
                color: #A8A8B3;
            }
            #CancelButton:hover {
                background-color: #15171C;
                color: #E1E1E6;
            }
            #CancelButton:pressed {
                background-color: #0D0F12;
            }
        """
        self.setStyleSheet(qss)
        logger.debug("QSS theme stylesheet applied successfully")

    def closeEvent(self, event):
        """Log deletion and let garbage collector clean it up immediately."""
        logger.info("SettingsDialog close event triggered. Cleaning up resources.")
        super().closeEvent(event)
