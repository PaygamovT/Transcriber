# Architecture: Layered Service-Oriented (MVC / Service-Presenter)

## Overview
For a lightweight, zero-footprint desktop application like Transcriber, we adopt a **Layered Service-Oriented Architecture** with a clear separation of concerns (MVC/Service-Presenter pattern). This architecture prioritizes minimal RAM footprint (~40-60MB), responsiveness, and strict thread separation. 

The application is structured into three primary layers:
1. **Presentation Layer (UI/Tray):** The `QSystemTrayIcon` and lazy-loaded, short-lived settings dialog.
2. **Orchestration Layer (App/Controller):** Handles hotkey events (`pynput`), thread workers, and coordinates between UI actions, audio capture, and translation services.
3. **Core Service Layer:** Decoupled services for Audio Capture (`sounddevice`/`numpy`) and Transcription (`OpenRouter` / `requests`).

---

## Decision Rationale
- **Project Type:** Single-purpose, event-driven desktop utility.
- **Tech Stack:** Python 3.12, `PyQt6`, `pynput`, `sounddevice`, `numpy`, `requests`.
- **Key Factor:** Low memory footprint and non-blocking GUI. PyQt6 widgets and event-loops are strictly isolated from I/O blockages (microphone recording and HTTP calls) using concurrent worker threads.

---

## Folder Structure
The codebase follows standard Python packaging structures:

```
Transcriber/
├── src/
│   ├── __init__.py
│   ├── main.py                   # Application entry point
│   ├── config.py                 # User configuration manager (JSON storage)
│   │
│   ├── ui/                       # Presentation Layer
│   │   ├── __init__.py
│   │   ├── tray.py               # PyQt6 QSystemTrayIcon & menu definitions
│   │   └── settings.py           # Lazy-instantiated Settings/Config Dialog
│   │
│   ├── orchestrator/             # Orchestration Layer
│   │   ├── __init__.py
│   │   ├── hotkey.py             # pynput listener and key binder
│   │   └── manager.py            # Main state manager coordinating system state
│   │
│   └── services/                 # Core Service Layer
│       ├── __init__.py
│       ├── audio.py              # Audio recorder service (sounddevice/numpy)
│       ├── transcription.py      # OpenRouter API client service (requests)
│       └── clipboard.py          # Clipboard injector and virtual keyboard typing
│
└── tests/                        # Testing suite (pytest-based)
```

---

## Dependency Rules
To maintain decoupling and ensure modularity, dependencies must flow strictly in one direction:

```
[Presentation / UI] ───> [Orchestrator] ───> [Core Services]
```

- ✅ **UI components** can trigger methods on the **Orchestrator**.
- ✅ **Orchestrator** manages and calls the **Core Services**.
- ✅ **Core Services** have ZERO knowledge of the UI layer. They communicate state changes back using standard Python callbacks or PyQt `pyqtSignal` events from threaded workers.
- ❌ **Core Services** must NEVER import PyQt UI modules or call UI elements directly.
- ❌ **UI layer** must NEVER perform direct blocking network or I/O calls.

---

## Layer/Module Communication
- **Signal-Slot Concurrency:** Worker threads inherit from `QThread` or `QRunnable` and emit `pyqtSignal` objects to notify the GUI of transcription progress, errors, or audio signal levels.
- **Callback Injection:** Services are instantiated as plain Python objects and injected with functional callbacks to avoid importing any PyQt dependencies.

---

## Key Principles
1. **Zero Idle GUI Footprint:** The settings window must be instantiated *only* when requested, and explicitly dereferenced and garbage collected upon closing to return RAM to the OS.
2. **Strict Thread Separation:** Standard sound recording (`sounddevice`) and OpenRouter HTTP requests (`requests`) run strictly on a background `QThread`. The PyQt main loop is solely responsible for rendering the tray icon, playing system alerts, or displaying tooltips.
3. **Single Responsibility:** The transcription client does not know how audio is recorded; the recorder does not know about the API. The `AppManager` binds them together.

---

## Code Examples

### 1. Lazy Settings Window Lifecycle (Presentation Layer)
This ensures the settings UI is loaded and immediately freed from RAM when closed, keeping memory usage at 40-60MB.

```python
# src/ui/tray.py
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QObject
from src.ui.settings import SettingsDialog

class TranscriberTray(QObject):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.tray_icon = QSystemTrayIcon()
        self.settings_window = None  # Lazy reference
        self.setup_tray()

    def setup_tray(self):
        menu = QMenu()
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)
        
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.manager.shutdown)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def show_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsDialog(self.manager.config)
            # Wipes window from memory when closed
            self.settings_window.finished.connect(self.cleanup_settings)
            self.settings_window.show()

    def cleanup_settings(self):
        if self.settings_window:
            self.settings_window.deleteLater()
            self.settings_window = None  # Free from memory
```

### 2.Decoupled Threaded Worker (Core Services)
All HTTP communications to OpenRouter are isolated in a worker thread.

```python
# src/services/transcription.py
from PyQt6.QtCore import QThread, pyqtSignal
import requests

class TranscriptionWorker(QThread):
    # Communication channels back to UI
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key: str, audio_data, sample_rate: int):
        super().__init__()
        self.api_key = api_key
        self.audio_data = audio_data
        self.sample_rate = sample_rate

    def run(self):
        try:
            # 1. Convert audio_data (numpy array) to bytes/wav in-memory
            # 2. Call OpenRouter API with requests
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "audio/wav"
            }
            # Simulated API Call
            response = requests.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers=headers,
                data=self.audio_data
            )
            response.raise_for_status()
            text = response.json().get("text", "")
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))
```

---

## Anti-Patterns
- ❌ **No UI Blocking:** Running audio capture or `requests.post` inside the main thread loop. This freezes the system tray menu and crashes hotkey listeners.
- ❌ **No UI Imports in Services:** Importing `PyQt6` inside `src/services/audio.py` or `src/services/transcription.py`.
- ❌ **No Persistent Windows:** Keeping the Settings dialog hidden (`window.hide()`) rather than deleted (`deleteLater()`). This balloons RAM usage and violates the 40-60MB target footprint.
