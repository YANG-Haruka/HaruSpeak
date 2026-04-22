"""OpenAI Whisper-compatible STT.

Works with:
- api.openai.com (whisper-1)
- OpenAI-compat proxies that support /v1/audio/transcriptions
  (jeniya.top, OpenRouter, etc.)

Browser records audio/webm/opus; Whisper accepts that natively.
"""
from __future__ import annotations

import io

from .base import Transcript


class OpenAIWhisperSTT:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "whisper-1",
        timeout_s: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._timeout_s = timeout_s
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout_s,   # default is 600s — way too long for a chat loop
        )
        return self._client

    async def transcribe(self, audio_bytes: bytes, language: str) -> Transcript:
        if not audio_bytes:
            return Transcript(text="", language=language)

        client = self._get_client()
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.webm"   # tells the server the mimetype

        lang_hint = language if language in {"ja", "zh", "en", "ko", "fr", "de", "es"} else None

        try:
            result = await client.audio.transcriptions.create(
                file=buf,
                model=self._model,
                language=lang_hint,
            )
            text = getattr(result, "text", "") or ""
            return Transcript(text=text.strip(), language=language)
        except Exception as e:
            # Surface the error in logs so we can see proxy issues etc.
            print(f"[whisper] transcription failed: {type(e).__name__}: {e}")
            return Transcript(text="", language=language)
