"""One-command installer for HaruSpeak.

Creates the conda env, installs ffmpeg + Python deps (via uv, ~10x faster
than pip), and sets up the frontend. Idempotent — safe to re-run anytime.

Prerequisites the user must have installed separately:
  - Python 3.11+ (to run *this* script)
  - Miniconda or Anaconda (for the isolated env + ffmpeg)
  - Node.js 18+ (for the frontend)

Usage:
    python scripts/setup.py                   # full setup
    python scripts/setup.py --backend-only    # skip npm install
    python scripts/setup.py --frontend-only   # skip conda / python deps
    python scripts/setup.py --recreate        # delete + recreate the env
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENV_NAME = "haruspeak"
PY_VERSION = "3.11"


# ---------------------------------------------------------------- style utils


def _print(msg: str, kind: str = "info") -> None:
    prefix = {
        "info": "  ",
        "step": "\n➜ ",
        "ok": "  ✓ ",
        "warn": "  ⚠ ",
        "error": "  ✗ ",
    }[kind]
    print(f"{prefix}{msg}", flush=True)


def _run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a command, streaming stdout/stderr to the console."""
    return subprocess.run(cmd, check=check, **kwargs)


def _has(bin_name: str) -> bool:
    return shutil.which(bin_name) is not None


# ---------------------------------------------------------------- preflight


def _preflight() -> None:
    _print("Checking prerequisites", "step")
    missing = []
    if not _has("conda"):
        missing.append("conda (install Miniconda or Anaconda)")
    if not _has("node") or not _has("npm"):
        missing.append("node / npm (install Node.js 18+)")
    if missing:
        for m in missing:
            _print(f"MISSING: {m}", "error")
        _print("Install the missing tools above, then rerun this script.", "error")
        sys.exit(1)
    _print("conda OK", "ok")
    _print("node + npm OK", "ok")


# ---------------------------------------------------------------- conda env


def _conda_env_exists(name: str) -> bool:
    """Use `conda env list --json` so we don't parse human text."""
    result = subprocess.run(
        ["conda", "env", "list", "--json"],
        capture_output=True, text=True, check=True,
    )
    envs = json.loads(result.stdout).get("envs", [])
    return any(Path(p).name == name for p in envs)


def _setup_conda_env(recreate: bool) -> None:
    _print(f"Conda env: {ENV_NAME}", "step")
    if _conda_env_exists(ENV_NAME):
        if recreate:
            _print(f"Removing existing {ENV_NAME}...", "info")
            _run(["conda", "env", "remove", "-n", ENV_NAME, "-y"])
        else:
            _print(f"Env '{ENV_NAME}' already exists — reusing.", "ok")
            return
    _print(f"Creating env with Python {PY_VERSION}...", "info")
    _run(["conda", "create", "-n", ENV_NAME, f"python={PY_VERSION}", "-y"])
    _print("env created", "ok")


def _install_ffmpeg() -> None:
    _print("ffmpeg (via conda-forge)", "step")
    _run(["conda", "install", "-n", ENV_NAME, "-c", "conda-forge", "ffmpeg", "-y"])
    _print("ffmpeg installed", "ok")


# ---------------------------------------------------------------- python deps


def _install_python_deps() -> None:
    _print("Python deps (via uv)", "step")
    req = ROOT / "backend" / "requirements.txt"
    if not req.exists():
        _print(f"Missing {req}", "error")
        sys.exit(1)
    # uv piggybacks on the conda env's pip; install it first.
    _run(["conda", "run", "-n", ENV_NAME, "--no-capture-output",
          "pip", "install", "uv", "--quiet"])
    _print("uv installed", "ok")
    # Then install everything with uv — ~10x faster than pip.
    _run(["conda", "run", "-n", ENV_NAME, "--no-capture-output",
          "uv", "pip", "install", "-r", str(req)])
    _print("python deps installed", "ok")


# ---------------------------------------------------------------- frontend


def _install_frontend() -> None:
    _print("Frontend deps (npm install)", "step")
    fe = ROOT / "frontend"
    if not (fe / "package.json").exists():
        _print(f"Missing {fe / 'package.json'}", "error")
        sys.exit(1)
    _run(["npm", "install"], cwd=str(fe))
    _print("frontend deps installed", "ok")


# ---------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description="HaruSpeak installer")
    parser.add_argument("--backend-only", action="store_true",
                        help="Skip npm install.")
    parser.add_argument("--frontend-only", action="store_true",
                        help="Skip conda / Python deps.")
    parser.add_argument("--recreate", action="store_true",
                        help=f"Delete '{ENV_NAME}' env and rebuild from scratch.")
    args = parser.parse_args()

    if args.backend_only and args.frontend_only:
        _print("Can't combine --backend-only with --frontend-only.", "error")
        sys.exit(1)

    _preflight()

    do_backend = not args.frontend_only
    do_frontend = not args.backend_only

    if do_backend:
        _setup_conda_env(recreate=args.recreate)
        _install_ffmpeg()
        _install_python_deps()

    if do_frontend:
        _install_frontend()

    _print("Done!", "step")
    _print("Start the app with:", "info")
    _print("    python scripts/dev.py", "info")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        _print(f"Command failed: {' '.join(e.cmd)}", "error")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        _print("Interrupted.", "warn")
        sys.exit(130)
