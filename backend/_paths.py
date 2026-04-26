"""Single source of truth for runtime paths.

Two execution modes:

  * dev — running `python -m uvicorn backend.main:app` from the repo
  * frozen — running `HaruSpeak.exe` produced by PyInstaller

In dev mode everything is relative to the repo root. In frozen mode
everything sits next to `HaruSpeak.exe` so the whole `dist/HaruSpeak/`
folder is portable: copy it anywhere, double-click, it works.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    """Folder that contains HaruSpeak.exe (frozen) or the repo (dev)."""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def models_dir() -> Path:
    return app_root() / "models"


def config_dir() -> Path:
    return app_root() / "config"


def prompts_dir() -> Path:
    return app_root() / "prompts"


def frontend_dir() -> Path:
    """Static frontend bundle (next build --output export). Frozen only."""
    return app_root() / "frontend"


def ffmpeg_exe() -> str | None:
    """Bundled ffmpeg.exe next to the launcher. None if not present
    (caller falls back to PATH)."""
    if not is_frozen():
        return None
    candidate = app_root() / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return str(candidate) if candidate.exists() else None
