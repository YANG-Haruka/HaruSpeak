"""edge-tts wrapper — Microsoft Edge Neural TTS, free and keyless.

Covers JA/ZH/EN/KR and many more with one library. Produces MP3 bytes.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

DEFAULT_VOICES: dict[str, str] = {
    "ja": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "en": "en-US-AriaNeural",
}


async def synthesize(text: str, lang: str, voice: str | None = None) -> bytes:
    """Synthesize `text` in the voice matching `lang`. Returns MP3 bytes.

    Returns b"" if the call fails (network, bad voice, etc.), so upstream
    callers can keep going without audio. Errors are *logged* — silently
    swallowing them once cost us hours debugging "no sound" after Microsoft
    retired several voices (e.g. ja-JP-AoiNeural) without notice.
    """
    if not text.strip():
        return b""
    try:
        import edge_tts
    except ImportError:
        log.warning("[tts] edge_tts not installed — skipping synthesis")
        return b""

    voice_name = voice or DEFAULT_VOICES.get(lang, "en-US-AriaNeural")
    try:
        communicate = edge_tts.Communicate(text, voice_name)
        buf: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                buf.append(chunk["data"])
        return b"".join(buf)
    except Exception as e:
        log.warning("[tts] %s synthesis failed for voice=%r: %s", lang, voice_name, e)
        return b""
