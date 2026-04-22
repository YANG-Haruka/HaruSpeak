"""Decode arbitrary audio bytes (webm/opus/mp4/wav/mp3) to 16 kHz mono float32.

The browser's MediaRecorder emits webm/opus which neither soundfile nor
funasr handle natively. We shell out to ffmpeg (installed via conda-forge)
to normalize into the same PCM representation.

Runs ffmpeg synchronously in a thread executor. Why not async?
    Windows: aiohttp (used by edge-tts) can switch the asyncio loop to
    WindowsSelectorEventLoopPolicy, which does NOT support
    asyncio.create_subprocess_exec → NotImplementedError.
    Using a sync subprocess inside run_in_executor sidesteps this entirely
    and costs only one extra thread hop per turn.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess

import numpy as np


TARGET_SR = 16_000


def _decode_sync(audio_bytes: bytes) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install via "
            "`conda install -n haruspeak -c conda-forge ffmpeg`."
        )

    # -f s16le 16-bit signed little-endian PCM → 2 bytes/sample → easy numpy decode
    argv = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-ac", "1",
        "-ar", str(TARGET_SR),
        "-f", "s16le",
        "pipe:1",
    ]
    # argv list with shell=False: no injection possible
    result = subprocess.run(
        argv,
        input=audio_bytes,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"ffmpeg decode failed (code {result.returncode}): {msg}")
    return np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0


async def decode_to_pcm16k(audio_bytes: bytes) -> np.ndarray:
    """Return float32 mono numpy array at 16 kHz. Empty array on empty input."""
    if not audio_bytes:
        return np.zeros(0, dtype=np.float32)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _decode_sync, audio_bytes)
