"""SenseVoice-Small wrapper (local inference via funasr).

Lazy-loads the model so unit tests don't pay the download cost.
Prefer the HuggingFace snapshot (fast) over the ModelScope default (slow CDN).
"""
from __future__ import annotations

import re
from pathlib import Path

from huggingface_hub import snapshot_download

from ..audio import decode_to_pcm16k
from .base import Transcript

# SenseVoice surrounds output with control tokens like <|ja|><|NEUTRAL|><|Speech|><|woitn|>
_TAG_RE = re.compile(r"<\|[^|]*\|>")


class SenseVoiceSTT:
    def __init__(self, model_path: str | None = None) -> None:
        # If path looks like a local dir, use as-is. Otherwise resolve via HF hub.
        self._model_path = model_path or "FunAudioLLM/SenseVoiceSmall"
        self._model = None

    def _resolve_local_path(self) -> str:
        p = self._model_path
        if Path(p).exists():
            return p
        # Prefer <repo>/models/sensevoice-small/ — that's where the UI
        # Download button puts freshly-fetched weights. Falls through to
        # HF hub if not found (auto-downloads into HF cache).
        repo_root = Path(__file__).resolve().parents[2]
        local = repo_root / "models" / "sensevoice-small"
        if local.is_dir() and any(local.iterdir()):
            cached = str(local)
        else:
            cached = snapshot_download(
                repo_id=p,
                ignore_patterns=["example/*", "*.mp3", "fig/*"],
            )
        # Neutralize the model-shipped requirements.txt — funasr otherwise
        # tries to pip-install it into the running env (usually fails with
        # a PermissionError since Anaconda's site-packages is read-only).
        req = Path(cached) / "requirements.txt"
        try:
            if req.exists() and req.stat().st_size > 0:
                req.write_text("")
        except OSError:
            pass  # HF symlink or permission — safe to ignore
        return cached

    def _load(self):
        if self._model is not None:
            return self._model
        from funasr import AutoModel  # type: ignore

        local = self._resolve_local_path()
        print(f"[sensevoice] loading from {local}")
        # No trust_remote_code — funasr has built-in SenseVoice support;
        # the flag only triggers a "No module named 'model'" warning.
        self._model = AutoModel(
            model=local,
            disable_update=True,
        )
        return self._model

    async def transcribe(self, audio_bytes: bytes, language: str) -> Transcript:
        if not audio_bytes:
            return Transcript(text="", language=language)

        # Browser sends webm/opus; SenseVoice expects PCM/numpy. Normalize via ffmpeg.
        pcm = await decode_to_pcm16k(audio_bytes)
        if pcm.size == 0:
            return Transcript(text="", language=language)

        model = self._load()
        try:
            result = model.generate(
                input=pcm,
                cache={},
                language=language,     # "ja" | "zh" | "en" | "ko" | "yue" | "auto"
                use_itn=True,
                batch_size_s=60,
            )
        except Exception as e:
            print(f"[sensevoice] transcribe failed: {type(e).__name__}: {e}")
            return Transcript(text="", language=language)

        text = ""
        if isinstance(result, list) and result:
            first = result[0]
            raw = first.get("text", "") if isinstance(first, dict) else str(first)
            text = _TAG_RE.sub("", raw).strip()
        return Transcript(text=text, language=language)
