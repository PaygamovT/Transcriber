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
│       ├── audio-transcriber
│       ├── pyqt6-ui-development-rules
│       └── python-design-patterns
├── .ai-factory/             # Project context and specifications
│   └── DESCRIPTION.md       # High-level architecture and requirements
├── .ai-factory.json         # AI Factory active agent configuration
├── .mcp.json                # Project-level Model Context Protocol settings
├── AGENTS.md                # This project map file
└── project.md               # User workspace documentation (initially blank)
```

## Key Entry Points
*(To be populated as code is written)*

| File | Purpose |
|------|---------|
| `main.py` | Upcoming entry point initializing the tray icon and hotkey listener |

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
