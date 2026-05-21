import logging
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QSpinBox, QComboBox, QPushButton, QFormLayout,
    QGroupBox
)
from PyQt6.QtCore import Qt
from src.config import ConfigManager

# Setup logging
logger = logging.getLogger("transcriber.settings")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class SettingsDialog(QDialog):
    """Sleek and premium configuration dialog for the Transcriber application."""
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        logger.debug("SettingsDialog.__init__ entering")
        self.config = config
        
        self.setWindowTitle("Настройки Transcriber")
        self.setMinimumSize(480, 480)
        # Ensure it gets deleted when closed to reclaim idle RAM (essential for 40-60MB target)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.setup_ui()
        self.load_settings()
        self.apply_theme()
        
        logger.debug("SettingsDialog.__init__ exiting successfully")

    def setup_ui(self):
        logger.debug("SettingsDialog.setup_ui entering")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header / Title
        header_label = QLabel("Параметры Transcriber")
        header_label.setObjectName("HeaderLabel")
        layout.addWidget(header_label)
        
        # Form Layout inside GroupBox
        form_group = QGroupBox()
        form_group.setObjectName("FormGroup")
        form_layout = QFormLayout(form_group)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)
        
        # 1. API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Вставьте ключ API OpenRouter...")
        form_layout.addRow(QLabel("API Ключ OpenRouter:"), self.api_key_input)
        
        # 2. Model dropdown
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "google/gemini-3.1-flash-lite",
            "openai/whisper-large-v3",
            "meta-llama/llama-3-70b-instruct"
        ])
        self.model_combo.setEditable(True)
        form_layout.addRow(QLabel("Модель транскрипции:"), self.model_combo)
        
        # 3. Hotkey
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("<ctrl>+<shift>+space")
        form_layout.addRow(QLabel("Глобальная горячая клавиша:"), self.hotkey_input)
        
        # 4. Safety duration limit
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 300)
        self.duration_spin.setSuffix(" сек")
        form_layout.addRow(QLabel("Лимит записи:"), self.duration_spin)
        
        # 5. Insert Mode dropdown
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Копировать в буфер (Clipboard)", "clipboard")
        self.mode_combo.addItem("Печатать на курсоре (Typewriter)", "typewriter")
        form_layout.addRow(QLabel("Режим вставки текста:"), self.mode_combo)
        
        # 5b. Transcription Mode dropdown
        self.transcription_mode_combo = QComboBox()
        self.transcription_mode_combo.addItem("Обычная транскрипция (Normal)", "normal")
        self.transcription_mode_combo.addItem("Очистка от повторов и пауз (Clean)", "clean")
        self.transcription_mode_combo.addItem("Очистка + Перевод на английский (Translate)", "translate")
        form_layout.addRow(QLabel("Режим транскрипции:"), self.transcription_mode_combo)
        
        # 6. System Prompt
        self.prompt_input = QTextEdit()
        self.prompt_input.setTabChangesFocus(True)
        self.prompt_input.setMaximumHeight(80)
        form_layout.addRow(QLabel("Системный промпт ИИ:"), self.prompt_input)
        
        layout.addWidget(form_group)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("SaveButton")
        self.save_button.clicked.connect(self.save_settings)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setObjectName("CancelButton")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        logger.debug("SettingsDialog.setup_ui exiting")

    def load_settings(self):
        logger.debug("SettingsDialog.load_settings entering")
        self.api_key_input.setText(self.config.get("api_key"))
        
        # Match model text
        model = self.config.get("model")
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setEditText(model)
            
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
        api_key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()
        hotkey = self.hotkey_input.text().strip()
        duration = self.duration_spin.value()
        insert_mode = self.mode_combo.currentData()
        transcription_mode = self.transcription_mode_combo.currentData()
        prompt = self.prompt_input.toPlainText().strip()
        
        logger.info("Saving settings from configuration dialog UI")
        self.config.set("api_key", api_key)
        self.config.set("model", model)
        self.config.set("hotkey", hotkey)
        self.config.set("audio_duration_limit", duration)
        self.config.set("insert_mode", insert_mode)
        self.config.set("transcription_mode", transcription_mode)
        self.config.set("system_prompt", prompt)
        
        logger.debug("SettingsDialog.save_settings exiting with accept")
        self.accept()

    def apply_theme(self):
        """Applies a sleek and premium dark QSS theme to the configuration UI."""
        logger.debug("SettingsDialog.apply_theme entering")
        qss = """
            QDialog {
                background-color: #121214;
                font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #C4C4CC;
                font-size: 12px;
                font-weight: 500;
            }
            #HeaderLabel {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            #FormGroup {
                border: 1px solid #202024;
                border-radius: 8px;
                background-color: #1A1A1E;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #202024;
                border: 1px solid #29292E;
                border-radius: 6px;
                padding: 6px 10px;
                color: #E1E1E6;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #8F2DFF;
                background-color: #25252A;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QPushButton {
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 16px;
            }
            #SaveButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8F2DFF, stop:1 #6200EE);
                color: #FFFFFF;
                border: none;
            }
            #SaveButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #A24BFF, stop:1 #7016FF);
            }
            #SaveButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7A1EFF, stop:1 #5300CC);
            }
            #CancelButton {
                background-color: transparent;
                border: 1px solid #29292E;
                color: #A8A8B3;
            }
            #CancelButton:hover {
                background-color: #202024;
                color: #E1E1E6;
            }
            #CancelButton:pressed {
                background-color: #1A1A1E;
            }
        """
        self.setStyleSheet(qss)
        logger.debug("QSS theme stylesheet applied successfully")

    def closeEvent(self, event):
        """Log deletion and let garbage collector clean it up immediately."""
        logger.info("SettingsDialog close event triggered. Cleaning up resources.")
        super().closeEvent(event)
