# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the tiny HaruSpeak launcher.

This is *not* the full app — just the small wrapper that spawns the
embedded Python. No torch, no funasr, no ML deps. Builds in ~30 sec.
"""
from pathlib import Path

REPO = Path(SPECPATH).parent

_icon = REPO / "scripts" / "_cache" / "icon.ico"
icon_path = str(_icon) if _icon.exists() else None

a = Analysis(
    [str(REPO / "scripts" / "launcher.py")],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    excludes=[
        # Aggressive exclude list — none of these are touched by launcher.py.
        "tkinter", "matplotlib", "PIL", "numpy", "scipy", "pandas",
        "pytest", "IPython", "jupyter", "sphinx", "test", "unittest",
        "torch", "torchaudio", "funasr", "faster_whisper", "ctranslate2",
        "huggingface_hub", "pydantic", "pydantic_settings", "fastapi",
        "uvicorn", "websockets", "openai", "edge_tts", "fugashi",
        "unidic_lite", "pypinyin", "phonemizer", "yaml", "PyYAML",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# --onefile equivalent: pack everything into a single HaruSpeak.exe.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HaruSpeak",
    icon=icon_path,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
