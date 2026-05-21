# AGENTS.md

> Project map for AI agents. Keep this file up-to-date as the project evolves.

## Project Overview
A lightweight, zero-footprint desktop utility written in Python that runs silently in the system tray. Upon triggering a global hotkey, it records the microphone input, captures audio, and transcribes it on-the-fly using the Gemini Flash model via the OpenRouter API.

## Tech Stack
- **Language:** Python 3.12.10
- **GUI & Tray System:** `PyQt6` (zero-footprint tray app with lazy settings UI)
- **Global Hotkey:** `pynput`
- **Audio Capture:** `sounddevice`, `numpy`
- **AI Backend:** `requests` (OpenRouter API)

## Project Structure
```
Transcriber/
├── .agent/                  # Built-in AI Factory rules, skills, and workflows
├── .agents/                 # Installed external skills
│   └── skills/              # External skills copied for Antigravity and other agents
├── .ai-factory/             # Project context and specifications
│   ├── DESCRIPTION.md       # High-level architecture and requirements
│   ├── ARCHITECTURE.md      # Folder structure and architectural design
│   └── plans/               # Feature plans
│       └── feature-initial-implementation.md
├── src/                     # Core Python source directory
│   ├── orchestrator/        # State coordination and input interception
│   │   ├── hotkey.py        # Global keyboard listener using pynput
│   │   └── manager.py       # Main state manager and thread controller
│   ├── services/            # Pure Python business logic services
│   │   ├── audio.py         # sounddevice audio PCM recording
│   │   ├── clipboard.py     # Clipboard copying and keyboard emulation
│   │   └── transcription.py # requests-based OpenRouter transcription API client
│   ├── ui/                  # PyQt6 presentation layer
│   │   ├── settings.py      # Lazy-loaded premium dark-themed settings window
│   │   └── tray.py          # System tray icon with dynamic states and context menu
│   ├── config.py            # Local settings JSON loading/saving
│   └── main.py              # Composition root and application entry point
├── tests/                   # Portably mocked headless test suite
│   ├── test_audio.py
│   ├── test_clipboard.py
│   ├── test_config.py
│   ├── test_hotkey.py
│   ├── test_manager.py
│   ├── test_settings.py
│   ├── test_transcription.py
│   └── test_tray.py
├── AGENTS.md                # This project map file
└── project.md               # User workspace documentation (initially blank)
```

## Key Entry Points

| File | Purpose |
|------|---------|
| `src/main.py` | Main composition root initializing the tray icon, configuration, and app manager |
| `src/config.py` | Configuration manager managing global state persistent JSON values |
| `src/orchestrator/manager.py` | Coordinator driving threading and state changes |


## Documentation
| Document | Path | Description |
|----------|------|-------------|
| README | README.md | Project landing page (Russian) |
| Getting Started | docs/getting-started.md | Prerequisites, installation and running guides |
| Configuration | docs/configuration.md | OpenRouter API, hotkey and insert mode setups |

## AI Context Files
| File | Purpose |
|------|---------|
| `AGENTS.md` | This file — project structure map |
| `.ai-factory/DESCRIPTION.md` | Project specification and tech stack |
| `.ai-factory/ARCHITECTURE.md` | Architecture decisions and guidelines |
| `CLAUDE.md` | Agent instructions and preferences |
