"""faster-whisper local STT — 240MB small model, CPU or CUDA.

Downloads from HuggingFace on first use, much faster than ModelScope.
Supports JA/ZH/EN with one model.
"""
from __future__ import annotations

from ..audio import decode_to_pcm16k
from .base import Transcript


class FasterWhisperSTT:
    def __init__(
        self,
        model_size: str = "small",      # tiny / base / small / medium / large-v3
        device: str = "auto",           # "cpu" | "cuda" | "auto"
        compute_type: str = "auto",     # "int8" for CPU speed, "float16" for GPU
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        from pathlib import Path

        from faster_whisper import WhisperModel  # type: ignore

        device = self._device
        compute = self._compute_type
        if device == "auto":
            try:
                import torch  # type: ignore
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"
        if compute == "auto":
            compute = "float16" if device == "cuda" else "int8"

        # WhisperModel accepts either a size keyword ("small") that auto-downloads
        # into the HF cache, or a local path. Prefer <app_root>/models/ if present.
        from .. import _paths
        local = _paths.models_dir() / f"faster-whisper-{self._model_size}"
        model_arg = str(local) if local.is_dir() and any(local.iterdir()) else self._model_size

        self._model = WhisperModel(
            model_arg,
            device=device,
            compute_type=compute,
        )
        print(f"[faster-whisper] loaded size={self._model_size} from={model_arg} device={device} compute={compute}")
        return self._model

    async def transcribe(self, audio_bytes: bytes, language: str) -> Transcript:
        if not audio_bytes:
            return Transcript(text="", language=language)

        pcm = await decode_to_pcm16k(audio_bytes)
        if pcm.size == 0:
            return Transcript(text="", language=language)

        # faster-whisper is synchronous; run in thread to avoid blocking the loop.
        import asyncio

        def _sync() -> str:
            try:
                model = self._load()
                lang_hint = language if language in {"ja", "zh", "en", "ko", "fr", "de", "es"} else None
                segments, info = model.transcribe(
                    pcm,
                    language=lang_hint,
                    vad_filter=False,   # our frontend VAD already did the work
                    beam_size=1,        # prioritize speed over last 1-2% accuracy
                )
                return "".join(seg.text for seg in segments).strip()
            except Exception as e:
                print(f"[faster-whisper] transcribe failed: {type(e).__name__}: {e}")
                return ""

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _sync)
        return Transcript(text=text, language=language)
