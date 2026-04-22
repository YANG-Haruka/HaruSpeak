from .base import STTBackend, Transcript
from .faster_whisper_local import FasterWhisperSTT
from .sensevoice import SenseVoiceSTT

__all__ = [
    "STTBackend",
    "Transcript",
    "FasterWhisperSTT",
    "SenseVoiceSTT",
    "make_stt",
]


def make_stt(settings):
    """Factory: pick STT backend based on settings.stt_provider.

    Two local providers:
      - "sensevoice"     → SenseVoice-Small (recommended, fastest)
      - "faster_whisper" → faster-whisper (pick size via settings.faster_whisper_size)
    """
    provider = settings.stt_provider.lower()
    if provider in ("faster_whisper", "fasterwhisper", "local_whisper"):
        return FasterWhisperSTT(
            model_size=settings.faster_whisper_size,
            device="auto",
        )
    if provider == "sensevoice":
        return SenseVoiceSTT(settings.sensevoice_model_path)
    raise ValueError(f"Unknown STT provider: {settings.stt_provider}")
