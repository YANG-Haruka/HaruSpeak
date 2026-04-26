"""Embeddable-Python build for the portable HaruSpeak.exe folder.

Why not PyInstaller for the whole thing?
  PyInstaller's frozen importer mishandles torch's recursive `_C` extension
  binding (see torch/__init__.py line ~290). The result is a runtime
  `NameError: name '_C' is not defined` that's nearly impossible to fix
  without invasive bytecode patching of torch itself. Fighting it cost
  hours; switching to embeddable Python ducks the whole problem because
  the bundled runtime is a *real* Python interpreter loading *real* .py
  files — exactly the same context that works in dev mode.

Architecture:
  1. download python-3.11.x-embed-amd64.zip (cached) → dist/HaruSpeak/python/
  2. enable site-packages in the embeddable's _pth file
  3. bootstrap pip
  4. pip install -r backend/requirements.txt into the embedded Python
  5. prune ML bloat we definitely don't need
  6. PyInstaller builds a TINY launcher.py → HaruSpeak.exe (no torch deps,
     so this build is ~30s and rock solid)
  7. copy backend/, frontend/out/, models/, prompts/, config/, ffmpeg.exe
     to the top of dist/HaruSpeak/
  8. verify

Output:
    dist/HaruSpeak/
      HaruSpeak.exe         (5 MB, PyInstaller'd launcher)
      ffmpeg.exe
      python/               (embeddable Python + ML deps)
      backend/              (.py source, editable)
      frontend/             (next build static)
      models/sensevoice-small/
      prompts/, config/

Distribute the folder as a zip. ~2-2.5 GB.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENV_NAME = "haruspeak"
IS_WIN = os.name == "nt"

PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

# Force UTF-8 stdout — Windows GBK can't print our progress glyphs.
if os.name == "nt" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _conda_env_python() -> Path:
    """Find python.exe inside the haruspeak conda env (build host)."""
    rel = "python.exe" if IS_WIN else "bin/python"
    home = Path.home()
    candidates = [home / ".conda" / "envs" / ENV_NAME / rel]
    for env_var in ("CONDA_ROOT", "ANACONDA_HOME"):
        base = os.environ.get(env_var)
        if base:
            candidates.append(Path(base) / "envs" / ENV_NAME / rel)
    if IS_WIN:
        for drive in ("C:", "D:"):
            candidates += [
                Path(f"{drive}\\Software\\Anaconda\\envs\\{ENV_NAME}\\{rel}"),
                Path(f"{drive}\\Anaconda3\\envs\\{ENV_NAME}\\{rel}"),
                Path(f"{drive}\\ProgramData\\Anaconda3\\envs\\{ENV_NAME}\\{rel}"),
            ]
    for c in candidates:
        if c.exists():
            return c
    try:
        import json
        out = subprocess.check_output(["conda", "info", "--envs", "--json"], text=True)
        for path in json.loads(out).get("envs", []):
            if Path(path).name == ENV_NAME:
                return Path(path) / rel
    except Exception:
        pass
    raise FileNotFoundError(
        f"Can't find python.exe for conda env '{ENV_NAME}'. Run scripts/setup.py first."
    )


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    print(f"\n→ {' '.join(str(c) for c in cmd)}", flush=True)
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=full_env, check=True)


def _download_cached(url: str, cache: Path) -> Path:
    """Download `url` to `cache`, skipping if already present. Returns cache path."""
    if cache.exists() and cache.stat().st_size > 0:
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}", flush=True)
    urllib.request.urlretrieve(url, str(cache))
    return cache


def _step_clean() -> None:
    for d in ("dist", "build"):
        p = ROOT / d
        if p.exists():
            print(f"  removing {p}")
            shutil.rmtree(p)


def _step_prepare_icon() -> Path | None:
    """Convert the master PNG icon into:
      * frontend/app/icon.png  — Next.js auto-attaches this as favicon
      * scripts/_cache/icon.ico — Windows multi-size icon for HaruSpeak.exe
    Returns the .ico path (or None if no master icon exists)."""
    src = ROOT / "ico" / "haruspeak.png"
    if not src.exists():
        print("\n[icon] no ico/haruspeak.png — skipping icon setup")
        return None
    print("\n[icon] preparing icon assets…")

    # Copy to Next.js's auto-favicon location.
    fe_dest = ROOT / "frontend" / "app" / "icon.png"
    shutil.copy2(src, fe_dest)
    print(f"  ✓ {fe_dest.relative_to(ROOT)}")

    # Build a multi-size .ico for the Windows launcher exe.
    # Pillow packs all sizes into one file; Windows picks the right
    # resolution per context (16x16 in tab, 256x256 in Explorer thumbnails).
    from PIL import Image
    ico_path = ROOT / "scripts" / "_cache" / "icon.ico"
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGBA")
    img.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"  ✓ {ico_path.relative_to(ROOT)} (multi-size 16-256)")

    # Also drop the .ico into Next.js's app folder so /favicon.ico (the
    # legacy probe browsers always make) resolves with 200 instead of 404.
    fe_ico = ROOT / "frontend" / "app" / "favicon.ico"
    shutil.copy2(ico_path, fe_ico)
    print(f"  ✓ {fe_ico.relative_to(ROOT)}")

    return ico_path


def _step_frontend_export() -> None:
    out = ROOT / "frontend" / "out"
    if out.exists():
        shutil.rmtree(out)
    print("\n[1/8] Building frontend (static export)…")
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise RuntimeError("npm not found on PATH. Install Node.js first.")
    _run([npm, "run", "build"], cwd=ROOT / "frontend", env={"BUILD_TARGET": "export"})
    if not out.is_dir() or not any(out.iterdir()):
        raise RuntimeError(f"Expected frontend/out/ but it's missing or empty: {out}")
    size_mb = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1024**2
    print(f"  ✓ {out} ({size_mb:.1f} MB)")


def _step_stage_ffmpeg() -> None:
    print("\n[2/8] Staging ffmpeg.exe…")
    target = ROOT / "scripts" / "_ffmpeg"
    target.mkdir(exist_ok=True)
    target_exe = target / ("ffmpeg.exe" if IS_WIN else "ffmpeg")
    if target_exe.exists():
        print(f"  ✓ already staged: {target_exe}")
        return
    src = shutil.which("ffmpeg.exe") if IS_WIN else shutil.which("ffmpeg")
    if not src:
        raise RuntimeError(
            "ffmpeg not found on PATH. Either install it system-wide or "
            "drop a static ffmpeg.exe at scripts/_ffmpeg/ffmpeg.exe and re-run."
        )
    shutil.copy2(src, target_exe)
    size_mb = target_exe.stat().st_size / 1024**2
    print(f"  ✓ copied {src} → {target_exe} ({size_mb:.1f} MB)")


def _step_extract_embedded_python(out: Path) -> Path:
    """Download embeddable Python and extract to out/python/. Patch _pth."""
    print(f"\n[3/8] Setting up embeddable Python {PYTHON_VERSION}…")
    cache = ROOT / "scripts" / "_cache" / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    _download_cached(PYTHON_EMBED_URL, cache)

    py_dir = out / "python"
    if py_dir.exists():
        shutil.rmtree(py_dir)
    py_dir.mkdir(parents=True)

    with zipfile.ZipFile(cache) as zf:
        zf.extractall(py_dir)

    # Edit the _pth file: enable site-packages and add the parent dir
    # (where backend/ lives) so `python -m backend` resolves.
    pth_files = list(py_dir.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError(f"No _pth file found in {py_dir}")
    pth = pth_files[0]
    new_content = (
        f"python{sys.version_info.minor}.zip\n"  # cosmetic; gets overwritten below
    )
    # Actually rebuild from scratch to avoid surprises:
    minor = PYTHON_VERSION.split(".")[1]
    pth.write_text(
        f"python3{minor}.zip\n"
        ".\n"
        "..\n"               # so `python -m backend` finds dist/HaruSpeak/backend/
        "Lib/site-packages\n"
        "import site\n",
        encoding="utf-8",
    )
    print(f"  ✓ extracted to {py_dir} ({sum(f.stat().st_size for f in py_dir.rglob('*') if f.is_file())/1024**2:.1f} MB)")
    print(f"  ✓ patched {pth.name}: enabled site, added Lib/site-packages and ..")
    return py_dir


def _step_install_pip(py_dir: Path) -> None:
    print("\n[4/8] Bootstrapping pip…")
    cache = ROOT / "scripts" / "_cache" / "get-pip.py"
    _download_cached(GET_PIP_URL, cache)
    _run([
        str(py_dir / "python.exe"), str(cache),
        "--no-warn-script-location",
    ])


def _step_install_requirements(py_dir: Path) -> None:
    print("\n[5/8] Installing backend requirements (slow, ~5 min)…")
    py_exe = py_dir / "python.exe"
    _run([
        str(py_exe), "-m", "pip", "install",
        "--no-warn-script-location",
        "--no-cache-dir",
        "-r", str(ROOT / "backend" / "requirements.txt"),
    ])


# Same prune list as before — these come bundled with torch/funasr but
# HaruSpeak's CPU inference path doesn't touch them.
_PRUNE_FROM_SITE_PACKAGES = [
    "nvidia",          # CUDA runtime stubs (we run CPU-only torch)
    "paddle",
    "paddlepaddle",
    "bitsandbytes",
    "cv2",
    "llvmlite",
    "av",
    "av.libs",
    "onnxruntime",
    "sklearn",
    "scikit_learn",
    "transformers",
    "accelerate",
    "tensorboard",
]


def _step_prune(py_dir: Path) -> None:
    """Trim site-packages bloat: known-unused ML libs + dev artifacts that
    sneak into a fresh `pip install` (test suites, .pyc caches, build tools)."""
    print("\n[6/8] Pruning unused ML bloat from python/Lib/site-packages…")
    sp = py_dir / "Lib" / "site-packages"
    saved = 0

    # Pass 1: whole-package removals (the developer's prune list + tools we
    # don't ship: pip & setuptools are runtime no-ops once dependencies are
    # already installed; babel is a sphinx dep we never call).
    full_remove = set(_PRUNE_FROM_SITE_PACKAGES) | {
        "pip", "setuptools", "wheel", "babel", "Babel",
    }
    for entry in sorted(sp.iterdir()):
        # `foo`, `foo.libs`, `foo-1.0.dist-info`
        name = entry.name.split("-")[0]
        bare = name[:-5] if name.endswith(".libs") else name
        if bare not in full_remove and name not in full_remove:
            continue
        size = (
            sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
            if entry.is_dir() else entry.stat().st_size
        )
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
        saved += size
        print(f"  removed {entry.name}  ({size / 1024**2:.1f} MB)")

    # Pass 2: __pycache__ everywhere — Python regenerates these at runtime.
    pyc_saved = 0
    for cache in sp.rglob("__pycache__"):
        if cache.is_dir():
            pyc_saved += sum(f.stat().st_size for f in cache.rglob("*") if f.is_file())
            shutil.rmtree(cache, ignore_errors=True)
    saved += pyc_saved
    print(f"  removed __pycache__ dirs  ({pyc_saved / 1024**2:.1f} MB)")

    # Pass 3: in-package test suites — never imported by production code.
    test_saved = 0
    for d in list(sp.rglob("*")):
        if not d.is_dir():
            continue
        if d.name not in ("tests", "test"):
            continue
        # Don't touch top-level `tests/` packages (some libs use that name
        # for actual code); only nested under another package.
        if d.parent == sp:
            continue
        test_saved += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        shutil.rmtree(d, ignore_errors=True)
    saved += test_saved
    print(f"  removed in-package tests/ dirs  ({test_saved / 1024**2:.1f} MB)")

    print(f"  total saved: {saved / 1024**3:.2f} GB")


def _step_build_launcher(out: Path) -> None:
    """PyInstaller a 30-line launcher.py. No ML deps → fast and reliable."""
    print("\n[7/8] Building launcher exe (PyInstaller, ~30 sec)…")
    py = _conda_env_python()
    try:
        subprocess.check_output([str(py), "-c", "import PyInstaller"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        print("  pyinstaller not installed in build env — installing…")
        _run([str(py), "-m", "pip", "install", "pyinstaller==6.10.0"])
    # Pin the fast pefile (see issue #8762).
    _run([str(py), "-m", "pip", "install", "--quiet", "pefile==2023.2.7"])

    spec = ROOT / "scripts" / "launcher.spec"
    work = ROOT / "build" / "launcher"
    _run([
        str(py), "-m", "PyInstaller", str(spec),
        "--noconfirm",
        "--distpath", str(work),
        "--workpath", str(work / "_work"),
    ], env={"PYTHONNOUSERSITE": "1"})

    src_exe = work / "HaruSpeak.exe"
    dst_exe = out / "HaruSpeak.exe"
    shutil.copy2(src_exe, dst_exe)
    print(f"  ✓ {dst_exe} ({src_exe.stat().st_size / 1024**2:.1f} MB)")


def _step_copy_assets(out: Path) -> None:
    print("\n[8/8] Copying assets to dist/HaruSpeak/…")
    pairs: list[tuple[Path, Path, str]] = [
        (ROOT / "backend",                              out / "backend",                  "backend (source)"),
        (ROOT / "frontend" / "out",                     out / "frontend",                 "frontend"),
        (ROOT / "models" / "sensevoice-small",          out / "models" / "sensevoice-small", "model"),
        (ROOT / "prompts",                              out / "prompts",                  "prompts"),
        (ROOT / "config" / "config.sample.json",        out / "config" / "config.sample.json", "config sample"),
        (ROOT / "scripts" / "_ffmpeg" / "ffmpeg.exe",   out / "ffmpeg.exe",               "ffmpeg"),
    ]
    for src, dst, label in pairs:
        if not src.exists():
            raise RuntimeError(f"missing source for {label}: {src}")
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)
        size_mb = (
            sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
            if dst.is_dir() else dst.stat().st_size
        ) / 1024**2
        print(f"  {label}: {size_mb:.1f} MB → {dst.relative_to(out)}")


def _folder_size_gb(p: Path) -> float:
    total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return total / 1024**3


def _step_verify(out: Path) -> None:
    print("\nVerifying output…")
    must_exist = [
        out / ("HaruSpeak.exe" if IS_WIN else "HaruSpeak"),
        out / "python" / "python.exe",
        out / "python" / "Lib" / "site-packages" / "torch" / "_C.cp311-win_amd64.pyd",
        out / "backend" / "__main__.py",
        out / "frontend" / "index.html",
        out / "models" / "sensevoice-small" / "model.pt",
        out / "prompts",
        out / "config" / "config.sample.json",
        out / ("ffmpeg.exe" if IS_WIN else "ffmpeg"),
    ]
    missing = [p for p in must_exist if not p.exists()]
    if missing:
        print("  ✗ missing files in dist/HaruSpeak/:")
        for m in missing:
            print(f"      {m.relative_to(out)}")
        sys.exit(1)
    size = _folder_size_gb(out)
    print(f"  ✓ all expected files present")
    print(f"  ✓ dist/HaruSpeak/ total size: {size:.2f} GB")
    print(f"\nDone.  Distribute the folder: {out}")
    print("       (Zip it; recipient unzips and double-clicks HaruSpeak.exe.)")


def _prevent_system_sleep() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    except Exception as e:
        print(f"  (couldn't pin sleep state: {e})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="wipe dist/ and build/ first")
    args = parser.parse_args()

    _prevent_system_sleep()

    if args.clean:
        _step_clean()

    out = ROOT / "dist" / "HaruSpeak"
    out.mkdir(parents=True, exist_ok=True)

    _step_prepare_icon()
    _step_frontend_export()
    _step_stage_ffmpeg()
    py_dir = _step_extract_embedded_python(out)
    _step_install_pip(py_dir)
    _step_install_requirements(py_dir)
    _step_prune(py_dir)
    _step_build_launcher(out)
    _step_copy_assets(out)
    _step_verify(out)


if __name__ == "__main__":
    main()
