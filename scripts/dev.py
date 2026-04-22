"""One-command dev launcher — backend + frontend, desktop only.

Spawns backend + frontend as children, shares the terminal's console so
Ctrl+C broadcasts to both. No cmd.exe, no batch wrappers.

Usage:
    python scripts/dev.py              # both + auto-open browser
    python scripts/dev.py --no-open
    python scripts/dev.py --backend-only
    python scripts/dev.py --frontend-only
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent.parent
IS_WIN = os.name == "nt"
ENV_NAME = "haruspeak"

if IS_WIN and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---- resolving real executables --------------------------------------------


def _conda_env_python(env_name: str) -> Path:
    rel = "python.exe" if IS_WIN else "bin/python"
    home = Path.home()
    candidates = [home / ".conda" / "envs" / env_name / rel]
    for env_root in ("CONDA_ROOT", "ANACONDA_HOME"):
        base = os.environ.get(env_root)
        if base:
            candidates.append(Path(base) / "envs" / env_name / rel)
    if IS_WIN:
        for drive in ("C:", "D:"):
            candidates.append(Path(f"{drive}\\Software\\Anaconda\\envs\\{env_name}\\{rel}"))
            candidates.append(Path(f"{drive}\\Anaconda3\\envs\\{env_name}\\{rel}"))
            candidates.append(Path(f"{drive}\\ProgramData\\Anaconda3\\envs\\{env_name}\\{rel}"))
    for c in candidates:
        if c.exists():
            return c
    try:
        import json
        out = subprocess.check_output(["conda", "info", "--envs", "--json"], text=True)
        for path in json.loads(out).get("envs", []):
            if Path(path).name == env_name:
                return Path(path) / rel
    except Exception:
        pass
    raise FileNotFoundError(f"Can't find python.exe for conda env '{env_name}'.")


def _next_js_entry() -> Path:
    p = ROOT / "frontend" / "node_modules" / "next" / "dist" / "bin" / "next"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing. Run `npm install` inside frontend/ first.")
    return p


def _node_exe() -> str:
    path = shutil.which("node.exe") or shutil.which("node")
    if not path:
        raise FileNotFoundError("node not found on PATH. Install Node.js first.")
    return path


# ---- child process glue ----------------------------------------------------


COLOR = {"backend": "\033[36m", "frontend": "\033[35m", "reset": "\033[0m"}


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _stream(name: str, proc: subprocess.Popen) -> None:
    prefix = f"{COLOR.get(name, '')}[{name}]{COLOR['reset']}"
    assert proc.stdout is not None
    for line in iter(proc.stdout.readline, ""):
        if not line:
            break
        sys.stdout.write(f"{prefix} {line}")
        sys.stdout.flush()


def _spawn(cmd: list[str], cwd: Path, extra_env: dict | None = None) -> subprocess.Popen:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _auto_open(port: int, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _port_in_use(port):
            webbrowser.open(f"http://localhost:{port}")
            return
        time.sleep(0.5)


def _shutdown(procs: list[tuple[str, subprocess.Popen]]) -> None:
    for name, proc in procs:
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            print(f"[{name}] didn't exit, force-killing")
            if IS_WIN:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="HaruSpeak dev launcher")
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--frontend-only", action="store_true")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="do NOT auto-open the browser",
    )
    args = parser.parse_args()

    if not args.frontend_only and _port_in_use(8000):
        print("! port 8000 already in use — close the previous backend and retry.")
        sys.exit(1)
    if not args.backend_only and _port_in_use(3000):
        print("! port 3000 already in use — close the previous frontend and retry.")
        sys.exit(1)

    procs: list[tuple[str, subprocess.Popen]] = []

    if not args.frontend_only:
        python = _conda_env_python(ENV_NAME)
        backend_cmd = [
            str(python),
            "-m", "uvicorn",
            "backend.main:app",
            "--reload",
            "--reload-dir", "backend",
            "--host", "127.0.0.1",
            "--port", "8000",
        ]
        backend_env = {"PYTHONNOUSERSITE": "1"}
        print(f"→ backend  : http://localhost:8000")
        procs.append(("backend", _spawn(backend_cmd, ROOT, extra_env=backend_env)))

    if not args.backend_only:
        node = _node_exe()
        next_entry = _next_js_entry()
        frontend_cmd = [node, str(next_entry), "dev"]
        print(f"→ frontend : http://localhost:3000")
        procs.append(("frontend", _spawn(frontend_cmd, ROOT / "frontend")))

    for name, proc in procs:
        threading.Thread(target=_stream, args=(name, proc), daemon=True).start()

    if not args.no_open and not args.backend_only:
        threading.Thread(target=_auto_open, args=(3000,), daemon=True).start()

    print("Press Ctrl+C once to stop both.\n")

    reported: set[str] = set()
    try:
        while True:
            for name, p in procs:
                if p.poll() is not None and name not in reported:
                    print(
                        f"\n[{name}] exited with code {p.returncode}. "
                        f"Scroll up for logs. Ctrl+C to stop the other service."
                    )
                    reported.add(name)
            if len(reported) == len(procs):
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n→ shutting down…")
    finally:
        _shutdown(procs)


if __name__ == "__main__":
    main()
