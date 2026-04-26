"""Tiny launcher exe — spawns the embedded Python with `-m backend`.

This is what the user double-clicks. It does almost nothing — the actual
HaruSpeak app runs as a child process inside the bundled Python.

Why a separate launcher?
  - The bundled Python (python\\python.exe) works perfectly but isn't
    branded "HaruSpeak". A 5 MB launcher with the right icon/name is the
    polish layer on top.
  - The embedded Python's CWD must be the parent of `backend/` so
    `python -m backend` resolves correctly. We set that here.

This script gets PyInstaller'd into HaruSpeak.exe. Because it has zero
ML dependencies, that build is fast (~30s) and rock solid.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if getattr(sys, "frozen", False):
        here = Path(sys.executable).parent
    else:
        # Dev mode: run from repo root.
        here = Path(__file__).resolve().parent.parent

    python_exe = here / "python" / "python.exe"
    if not python_exe.exists():
        print(f"[HaruSpeak] expected {python_exe} but it's missing.", file=sys.stderr)
        print("[HaruSpeak] re-extract the HaruSpeak folder and try again.", file=sys.stderr)
        input("Press Enter to exit…")
        return 1

    # `python -m backend` runs backend/__main__.py with the right package
    # context. cwd ensures `import backend` and friends resolve.
    return subprocess.call([str(python_exe), "-m", "backend"], cwd=str(here))


if __name__ == "__main__":
    sys.exit(main())
