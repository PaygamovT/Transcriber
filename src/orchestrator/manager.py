import logging
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from typing import Optional

from src.config import ConfigManager
from src.services.audio import AudioRecorder
from src.services.transcription import TranscriptionService
from src.services.clipboard import ClipboardService
from src.orchestrator.hotkey import HotkeyListener

# Setup logging
logger = logging.getLogger("transcriber.manager")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class TranscriptionWorker(QThread):
    """Background worker thread to run transcription without freezing the GUI."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, service: TranscriptionService, wav_bytes: bytes, mode: str = "normal"):
        super().__init__()
        self.service = service
        self.wav_bytes = wav_bytes
        self.mode = mode
        logger.debug(f"TranscriptionWorker initialized with mode: {mode}")

    def run(self):
        logger.debug(f"TranscriptionWorker thread run starting. Mode: {self.mode}")
        try:
            text = self.service.transcribe(self.wav_bytes, self.mode)
            logger.debug("TranscriptionWorker thread completed successfully")
            self.finished.emit(text)
        except Exception as e:
            logger.error(f"TranscriptionWorker thread encountered error: {e}", exc_info=True)
            self.error.emit(str(e))

class AppManager(QObject):
    """Main application coordinator that manages states and coordinates background worker tasks."""
    
    state_changed = pyqtSignal(str)  # Emitted when state changes ("idle", "recording", "transcribing")
    notification_requested = pyqtSignal(str, str)  # Title, Message (for tray notifications)
    hotkey_triggered = pyqtSignal()  # Internal signal used to marshal pynput thread trigger to GUI thread
    segment_captured = pyqtSignal(bytes)  # Emitted thread-safely when a silent slice is captured

    def __init__(self, 
                 config: ConfigManager, 
                 recorder: Optional[AudioRecorder] = None,
                 clipboard: Optional[ClipboardService] = None):
        super().__init__()
        logger.debug("AppManager.__init__ entering")
        self.config = config
        
        # Dependency Injection / Fallbacks
        self.recorder = recorder or AudioRecorder(sample_rate=16000, channels=1)
        
        if clipboard is None:
            self.clipboard = ClipboardService(clipboard_setter_callback=self._set_clipboard_data)
        else:
            self.clipboard = clipboard
            
        provider = self.config.get("provider")
        chat_model = self.config.get(f"{provider}_chat_model") if provider in ("openai", "groq") else None
        self.transcription_service = TranscriptionService(
            api_key=self.config.get("api_key"),
            model=self.config.get("model"),
            system_prompt=self.config.get("system_prompt"),
            provider=provider,
            chat_model=chat_model
        )

        
        self.state = "idle"
        self.hotkey_listener: Optional[HotkeyListener] = None
        self.worker: Optional[TranscriptionWorker] = None
        
        # Safety duration limit timer
        self.limit_timer = QTimer()
        self.limit_timer.setSingleShot(True)
        self.limit_timer.timeout.connect(self.stop_recording)
        
        # Connect signals for thread-safe cross-thread UI marshaling
        self.hotkey_triggered.connect(self._handle_hotkey_trigger)
        self.segment_captured.connect(self._handle_segment_captured)
        
        # Active segment workers set to prevent garbage collection
        self.active_segment_workers = set()
        
        # Wire recorder silence detection callback
        self.recorder.silence_detected_callback = self._on_recorder_silence
        
        # Initialize and start global hotkey
        self.setup_hotkey()
        
        logger.debug("AppManager.__init__ exiting successfully")

    def _set_clipboard_data(self, text: str) -> None:
        """Helper callback to set system clipboard utilizing PyQt6 QApplication."""
        logger.debug("AppManager._set_clipboard_data entering")
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            clipboard = app.clipboard()
            clipboard.setText(text)
            logger.debug("Text successfully copied to system clipboard via QApplication")
        else:
            logger.warning("Could not set clipboard: QApplication instance not initialized.")
        logger.debug("AppManager._set_clipboard_data exiting")

    def setup_hotkey(self) -> None:
        """Sets up and starts the global hotkey listener based on the active config."""
        logger.debug("AppManager.setup_hotkey entering")
        if self.hotkey_listener:
            try:
                logger.debug("Stopping existing hotkey listener")
                self.hotkey_listener.stop()
            except Exception as e:
                logger.error(f"Error stopping hotkey listener: {e}")
                
        hotkey_str = self.config.get("hotkey")
        # Direct callback to emit hotkey_triggered signal. Since emit is thread-safe
        # and marshaled, this guarantees all GUI updates happen on the main GUI thread.
        self.hotkey_listener = HotkeyListener(hotkey_str, self._emit_hotkey_signal)
        self.hotkey_listener.start()
        logger.debug("AppManager.setup_hotkey exiting")

    def _emit_hotkey_signal(self) -> None:
        """Internal callback executed on pynput background listener thread."""
        logger.debug("Hotkey event received on background thread, emitting signal")
        self.hotkey_triggered.emit()

    def _handle_hotkey_trigger(self) -> None:
        """Thread-safely handles the hotkey trigger on the main GUI thread."""
        logger.debug(f"AppManager._handle_hotkey_trigger entering. Current state: {self.state}")
        if self.state == "idle":
            self.start_recording()
        elif self.state == "recording":
            self.stop_recording()
        else:
            logger.warning(f"Hotkey trigger ignored because manager state is: {self.state}")

    def start_recording(self) -> None:
        """Starts the audio recording process."""
        logger.debug("AppManager.start_recording entering")
        if self.state != "idle":
            logger.warning(f"Cannot start recording from state: {self.state}")
            return
            
        try:
            self._set_state("recording")
            # Sync any new settings
            provider = self.config.get("provider")
            self.transcription_service.provider = provider
            self.transcription_service.chat_model = self.config.get(f"{provider}_chat_model") if provider in ("openai", "groq") else None
            self.transcription_service.api_key = self.config.get("api_key")
            self.transcription_service.model = self.config.get("model")
            self.transcription_service.system_prompt = self.config.get("system_prompt")
            
            # Reset active segment workers and context
            self.active_segment_workers.clear()
            self.transcription_service.last_context = ""
            
            # Enable silence detection strictly in normal transcription mode
            mode = self.config.get("transcription_mode") or "normal"
            silence_enabled = (mode == "normal")
            
            logger.debug(f"Starting recorder with silence_detection_enabled={silence_enabled}")
            self.recorder.start_recording(silence_detection_enabled=silence_enabled)
            
            # Start safety limit timer
            limit_s = self.config.get("audio_duration_limit")
            logger.debug(f"Starting safety limit timer for {limit_s} seconds")
            self.limit_timer.start(limit_s * 1000)
            
            self.notification_requested.emit("Transcriber", "Запись началась... Говорите!")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}", exc_info=True)
            self._set_state("idle")
            self.notification_requested.emit("Ошибка", f"Не удалось начать запись: {e}")
            
        logger.debug("AppManager.start_recording exiting")

    def stop_recording(self) -> None:
        """Stops the audio recording and triggers the transcription worker thread."""
        logger.debug("AppManager.stop_recording entering")
        if self.state != "recording":
            logger.warning(f"Cannot stop recording from state: {self.state}")
            return
            
        try:
            # Stop the safety limit timer
            self.limit_timer.stop()
            
            logger.debug("Stopping recorder and retrieving WAV bytes")
            wav_bytes = self.recorder.stop_recording()
            
            if not wav_bytes:
                logger.warning("No audio data was recorded")
                self._set_state("idle")
                mode = self.config.get("transcription_mode") or "normal"
                if mode != "normal":
                    self.notification_requested.emit("Предупреждение", "Запись пуста, транскрипция отменена.")
                return
                
            self._set_state("transcribing")
            logger.info("Initializing TranscriptionWorker background thread")
            mode = self.config.get("transcription_mode") or "normal"
            logger.info(f"Retrieved transcription mode: {mode}")
            self.worker = TranscriptionWorker(self.transcription_service, wav_bytes, mode=mode)
            self.worker.finished.connect(self._handle_transcription_success)
            self.worker.error.connect(self._handle_transcription_error)
            self.worker.start()
            logger.info("TranscriptionWorker started successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop recording or start worker: {e}", exc_info=True)
            self._set_state("idle")
            self.notification_requested.emit("Ошибка", f"Произошла ошибка при завершении записи: {e}")
            
        logger.debug("AppManager.stop_recording exiting")

    def _handle_transcription_success(self, text: str) -> None:
        """Processes the successfully transcribed text."""
        logger.debug("AppManager._handle_transcription_success entering")
        self._set_state("idle")
        self.worker = None
        
        cleaned_text = text.strip()
        if not cleaned_text:
            logger.info("Transcription returned empty text")
            self.notification_requested.emit("Транскрипция", "Речь не распознана.")
            return
            
        logger.info(f"Transcription successful. Text length: {len(cleaned_text)}")
        
        insert_mode = self.config.get("insert_mode")
        try:
            if insert_mode == "clipboard":
                logger.debug("Copying text to clipboard")
                self.clipboard.copy_to_clipboard(cleaned_text)
                self.notification_requested.emit("Транскрипция", "Текст скопирован в буфер обмена!")
            elif insert_mode == "typewriter":
                logger.debug("Typing text via keyboard emulation")
                self.clipboard.type_text(cleaned_text)
                logger.info("Text successfully typed")
            else:
                logger.warning(f"Unknown insert mode: {insert_mode}")
        except Exception as e:
            logger.error(f"Failed to output transcribed text: {e}", exc_info=True)
            self.notification_requested.emit("Ошибка вывода", f"Не удалось вывести текст: {e}")
            
        logger.debug("AppManager._handle_transcription_success exiting")

    def _handle_transcription_error(self, error_msg: str) -> None:
        """Handles transcription thread errors."""
        logger.debug("AppManager._handle_transcription_error entering")
        self._set_state("idle")
        self.worker = None
        
        logger.error(f"Transcription background worker failed: {error_msg}")
        self.notification_requested.emit("Ошибка транскрипции", f"Не удалось распознать аудио: {error_msg}")
        logger.debug("AppManager._handle_transcription_error exiting")

    def _on_recorder_silence(self, wav_bytes: bytes) -> None:
        """Callback from sounddevice InputStream thread when silence is detected."""
        logger.debug("Recorder detected silence segment, emitting segment_captured signal")
        self.segment_captured.emit(wav_bytes)

    def _handle_segment_captured(self, wav_bytes: bytes) -> None:
        """Handles a captured silence segment on the main thread."""
        logger.debug(f"AppManager._handle_segment_captured entering. Current state: {self.state}")
        
        # Only process segment transcription if we are in normal transcription mode AND state is recording
        mode = self.config.get("transcription_mode") or "normal"
        if mode != "normal" or self.state != "recording":
            logger.warning(f"Segment ignored: mode={mode}, state={self.state}")
            return
            
        logger.info("Initializing parallel TranscriptionWorker for segment")
        worker = TranscriptionWorker(self.transcription_service, wav_bytes, mode=mode)
        
        # Track worker to avoid garbage collection
        self.active_segment_workers.add(worker)
        
        # Connect signals
        worker.finished.connect(lambda text, w=worker: self._handle_segment_success(text, w))
        worker.error.connect(lambda error_msg, w=worker: self._handle_segment_error(error_msg, w))
        
        worker.start()
        logger.info(f"Parallel TranscriptionWorker started for segment. Active segment workers: {len(self.active_segment_workers)}")

    def _handle_segment_success(self, text: str, worker: TranscriptionWorker) -> None:
        """Processes successfully transcribed segment text."""
        logger.debug("AppManager._handle_segment_success entering")
        if worker in self.active_segment_workers:
            self.active_segment_workers.remove(worker)
            
        cleaned_text = text.strip()
        if not cleaned_text:
            logger.info("Segment transcription returned empty text")
            return
            
        logger.info(f"Segment transcription successful. Text: {cleaned_text}")
        
        insert_mode = self.config.get("insert_mode")
        try:
            if insert_mode == "clipboard":
                logger.debug("Copying segment text to clipboard")
                self.clipboard.copy_to_clipboard(cleaned_text)
                self.notification_requested.emit("Транскрипция", "Сегмент скопирован в буфер обмена!")
            elif insert_mode == "typewriter":
                logger.debug("Typing segment text via keyboard emulation")
                self.clipboard.type_text(cleaned_text)
                logger.info("Segment text successfully typed")
            else:
                logger.warning(f"Unknown insert mode: {insert_mode}")
        except Exception as e:
            logger.error(f"Failed to output segment text: {e}", exc_info=True)
            self.notification_requested.emit("Ошибка вывода сегмента", f"Не удалось вывести сегмент: {e}")
            
        logger.debug("AppManager._handle_segment_success exiting")

    def _handle_segment_error(self, error_msg: str, worker: TranscriptionWorker) -> None:
        """Processes failed segment transcription."""
        logger.debug("AppManager._handle_segment_error entering")
        if worker in self.active_segment_workers:
            self.active_segment_workers.remove(worker)
            
        logger.error(f"Segment transcription failed: {error_msg}")
        self.notification_requested.emit("Ошибка сегмента", f"Не удалось распознать сегмент: {error_msg}")
        logger.debug("AppManager._handle_segment_error exiting")

    def reload_configuration(self) -> None:
        """Reloads the active configuration and updates services."""
        logger.info("Reloading configuration and resetting services")
        # Reload values from configuration file
        self.config.load()
        # Re-initialize the hotkey listener
        self.setup_hotkey()
        # Update model settings on the transcription service
        provider = self.config.get("provider")
        self.transcription_service.provider = provider
        self.transcription_service.chat_model = self.config.get(f"{provider}_chat_model") if provider in ("openai", "groq") else None
        self.transcription_service.api_key = self.config.get("api_key")
        self.transcription_service.model = self.config.get("model")
        self.transcription_service.system_prompt = self.config.get("system_prompt")
        logger.info("Configuration successfully reloaded")

    def shutdown(self) -> None:
        """Performs a clean shutdown, stopping listeners, recorders, and workers."""
        logger.info("AppManager shutdown requested")
        
        if self.limit_timer.isActive():
            self.limit_timer.stop()
            
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception as e:
                logger.error(f"Error stopping hotkey listener during shutdown: {e}")
                
        if self.state == "recording":
            try:
                self.recorder.stop_recording()
            except Exception as e:
                logger.error(f"Error stopping recorder during shutdown: {e}")
                
        # Clean up any active segment workers
        for worker in list(self.active_segment_workers):
            if worker.isRunning():
                worker.terminate()
                worker.wait()
        self.active_segment_workers.clear()
        
        if self.worker and self.worker.isRunning():
            logger.info("Waiting for transcription worker to finish")
            self.worker.terminate()
            self.worker.wait()
            
        logger.info("AppManager successfully shut down")

    def _set_state(self, new_state: str) -> None:
        """Internal helper to set states and emit notifications."""
        logger.info(f"AppManager state transitioning: {self.state} -> {new_state}")
        self.state = new_state
        self.state_changed.emit(self.state)
