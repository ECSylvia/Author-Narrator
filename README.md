# Author-Narrator

## 2.0 local browser workspace

From this folder, run `python local_web.py` and open http://127.0.0.1:8765.
This browser version needs only Python and Windows' built-in System.Speech:
no pip packages, API key, or cloud deployment. Stop it with Ctrl+C.

Import a UTF-8 `.txt` or `.md` manuscript (up to 4 MB), edit chapters,
preview their opening, generate a chapter, listen, download a WAV, and mark
the chapter reviewed. Project edits save automatically under `local_data/`,
alongside generated audio. Export project backup downloads a JSON snapshot;
audio remains in `local_data/`, so preserve that folder for a complete backup.
This first version stores one active project. Importing replaces it after confirmation.

**Current narration uses installed Windows voices, not a cloned author voice.**
The commercially permissible self-hosted cloning engine and distributor-ready
audiobook export are still pending. WAV output here is a local workflow proof,
not a distributor compliance guarantee. The server binds only to loopback.
Do not expose this development server to a network.

The original desktop application below remains available separately.

An app to allow authors to create an audiobook in their own voice using AI voice cloning via the [ElevenLabs](https://elevenlabs.io) API.

## Features

- **Manuscript import** — Import `.md` or `.txt` files; chapters are auto-detected (supports "Chapter One", "Prologue", "Epilogue", etc.)
- **Voice cloning** — Record a voice sample and create an Instant Voice Clone on ElevenLabs
- **Sample preview** — Generate a short TTS preview (~1000 chars) of any chapter before committing
- **Per-chapter generation** — Generate audio for a single chapter or the entire book
- **Cost estimation** — Right-hand sidebar shows estimated ElevenLabs API cost per chapter and for the full manuscript
- **Pause / resume / cancel** — Full audiobook generation runs in a background thread with controls

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [ffmpeg](https://ffmpeg.org/) (for compressing voice samples before upload)
- An [ElevenLabs API key](https://elevenlabs.io/app/settings/api-keys)

## Quick Start

```bash
# Install dependencies
uv sync

# Run the app
uv run python src/main.py
```

## First-Time Setup

1. **Create a project** from the welcome screen
2. **Complete the consent wizard** — record a voice sample (read the provided script)
3. **Set your API key** — go to Edit → Preferences and paste your ElevenLabs API key
4. **Import a manuscript** — click "Import Manuscript" and select a `.txt` or `.md` file

## Usage

- Select a chapter in the sidebar to view its text
- Click **"Preview Sample"** to hear a short TTS preview of the chapter opening
- Click **"Generate This Chapter"** to produce audio for the selected chapter
- Click **"Generate Full Audiobook"** to batch-generate all chapters
- The **cost panel** on the right shows character counts and estimated API costs

## Project Structure

```
src/
├── main.py                  # Entry point
├── core/
│   ├── audio_recorder.py    # Microphone recording (WAV)
│   ├── elevenlabs_generator.py  # Voice cloning & TTS
│   ├── manuscript_parser.py # Chapter detection for .md/.txt
│   ├── project_manager.py   # Project create/load/save
│   ├── settings_manager.py  # API key persistence
│   └── version_manager.py   # Version tracking
└── ui/
    ├── audiobook_dialog.py  # Full audiobook generation dialog
    ├── consent_wizard.py    # Voice recording consent flow
    ├── main_window.py       # Main application window
    ├── settings_dialog.py   # API key settings
    ├── voice_tools.py       # Voice review & sample playback
    └── welcome_screen.py    # Welcome / project picker
```

## License

Copyright © Doxie Enterprises, LLC 2026. All Rights Reserved.

## Doxie Hub integration

Open Author Narrator from the Hub dashboard at http://127.0.0.1:5173/narrator/.
Keep `python local_web.py` running on Windows; the Hub container proxies to
this loopback-only service through Docker Desktop. A return-to-Hub link is
included. Restart the Python service after updates and after Windows restarts.
This integration continues to use the single active project in `local_data/`;
it does not yet map separate Hub projects or connect voice cloning.

Tests: `python -m unittest discover -s tests -v`.
Optional isolated real Windows speech check:
`python -m unittest discover -s tests -p check_windows_speech.py -v`.
The latter uses a temporary data directory and never touches your manuscript.
