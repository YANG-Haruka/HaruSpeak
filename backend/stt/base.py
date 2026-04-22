from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class Transcript(BaseModel):
    text: str
    language: str
    confidence: float = 1.0


class STTBackend(Protocol):
    async def transcribe(self, audio_pcm16: bytes, language: str) -> Transcript: ...
