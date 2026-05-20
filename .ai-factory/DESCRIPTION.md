# Project: Transcriber

## Overview
A lightweight, zero-footprint desktop utility written in Python that runs silently in the system tray. Upon triggering a global hotkey, it records the microphone input, captures audio, and transcribes it on-the-fly using the Gemini Flash model via the OpenRouter API, putting the resulting text directly into the user's clipboard or typing it at the current cursor.

## Core Features
- **System Tray Operation:** Runs completely hidden in the Windows System Tray / macOS Menu Bar with no main window shown on launch.
- **Resource Optimized:** Instantiates its settings window on demand. Closing the settings window completely wipes it from RAM to keep memory usage at ~40-60MB.
- **Global Hotkey:** Listens for exactly one global hotkey (e.g., `Ctrl+Shift+Space` on Windows) using `pynput` to trigger audio capture.
- **Audio Capture:** Captures high-quality microphone input using `sounddevice` and `numpy`.
- **AI Transcription Backend:** Transcribes audio using OpenRouter API, specifically targeting `google/gemini-flash-1.5` (or latest available Gemini Flash model) via Python `requests`.
- **Seamless Output:** Inserts the transcribed text directly into the clipboard or types it at the current cursor position.

## Tech Stack
- **Language:** Python 3.10+
- **GUI & Tray System:** `PyQt6`
- **Global Hotkey:** `pynput`
- **Audio Capture:** `sounddevice`, `numpy`
- **AI Backend:** `requests` (OpenRouter API)
- **Transcription Model:** `google/gemini-flash-1.5`

## Architecture
See [.ai-factory/ARCHITECTURE.md](file:///c:/Users/tolib/Documents/GitHub/Transcriber/.ai-factory/ARCHITECTURE.md) for detailed architecture guidelines.
Pattern: Layered Service-Oriented (MVC / Service-Presenter)

## Architecture Notes
- **Tray-First Architecture:** The application entry point initializes a `QSystemTrayIcon` and registers system-wide key listeners.
- **Lazy Settings GUI:** The Settings/Config dialog is created on-demand when "Settings" is clicked from the tray menu and destroyed/freed immediately upon closing to minimize memory footprint.
- **Threaded Audio Recording & AI Calls:** Audio recording and API calls are handled on worker threads to prevent GUI freezing.
- **State Management:** Simple configuration stored locally (e.g., via `json` or `ini` file) for OpenRouter API keys, preferred hotkey, and prompt settings.

## Non-Functional Requirements
- **Logging:** Configurable via standard Python `logging` module, respecting `LOG_LEVEL` environment variable.
- **Memory Footprint:** Actively minimize memory footprint (~40-60MB idle) by avoiding loading heavy packages unless needed and purging GUI instances.
- **Error Handling:** Robust error handling for network dropouts, unauthorized API keys, and missing microphone devices, raising friendly notifications through the system tray.
- **Security:** OpenRouter API keys must be stored securely (e.g., user's config file with read/write restrictions or system keyring).
