"""HaruSpeak launcher — entry point for the frozen PyInstaller build.

What this does when the user double-clicks HaruSpeak.exe:
  1. Starts uvicorn serving backend.main:app on 127.0.0.1:8000.
  2. Polls the port in a background thread; once it's listening, opens
     the user's default browser to the right page.
  3. Blocks until the user closes the console window or hits Ctrl+C.

Why a custom launcher (instead of just `python -m uvicorn`)?
  Frozen PyInstaller bundles don't expose a python CLI, so uvicorn has
  to be invoked programmatically.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT = 8000
HOST = "127.0.0.1"


def _wait_for_port(host: str, port: int, timeout_s: float = 60.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.3)
    return False


def _first_launch_url(host: str, port: int) -> str:
    """Always open the language picker (homepage). Users who need to
    configure LLM settings reach them via the ⚙ icon in the top-right.

    Earlier this function smart-routed first-time users to /settings/, but
    the settings page's back button calls router.back() which depends on
    browser history. On a fresh launch there *is* no history, so the
    user gets stranded with no way home."""
    return f"http://{host}:{port}/"


def _open_browser_when_ready() -> None:
    if _wait_for_port(HOST, PORT):
        webbrowser.open(_first_launch_url(HOST, PORT))


def main() -> None:
    # Belt and braces: ensure we can find our own modules. Frozen PyInstaller
    # already sets sys.path correctly, but a stray cwd shouldn't break us.
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys.executable).parent
        sys.path.insert(0, str(bundle_dir))

    # Open the browser as soon as the server is up.
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    print(f"HaruSpeak running at http://{HOST}:{PORT}")
    print("Close this window to stop the server.")

    # Import the FastAPI app object directly and pass it to uvicorn.
    # The string form ("backend.main:app") would force uvicorn to importlib
    # the module by name, which fails in the frozen bundle because the
    # `backend` package isn't reachable as a top-level name from the
    # PyInstaller entry-point context.
    import uvicorn
    from backend.main import app

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
        # No --reload; this is a packaged build.
    )


if __name__ == "__main__":
    main()
