from __future__ import annotations

from typing import Sequence

from ..base import (
    AnnotatedText,
    ErrorPatternLib,
    LanguageModule,
    Phoneme,
    ProsodyPattern,
    ProsodyScore,
)
from .annotator import annotate as _annotate
from .errors import common_errors as _common_errors
from .g2p import g2p as _g2p
from .prosody import prosody_target as _prosody_target, score_prosody as _score_prosody


class CantoneseModule(LanguageModule):
    # Use ISO 639-3 `yue` (matches SenseVoice's language_code) rather than
    # BCP-47 `zh-HK`. The TTS layer maps yue → zh-HK-* voice IDs internally.
    code = "yue"
    display_names = {
        "ja": "広東語",
        "zh": "粤语",
        "en": "Cantonese",
        "ko": "광둥어",
        "yue": "粵語",
    }
    unit_kind = "syllable"

    def g2p(self, text: str) -> list[Phoneme]:
        return _g2p(text)

    def annotate(self, text: str) -> AnnotatedText:
        return _annotate(text)

    def prosody_target(self, text: str) -> ProsodyPattern:
        return _prosody_target(text)

    def score_prosody(
        self,
        user_f0: Sequence[float],
        user_times_ms: Sequence[int],
        target: ProsodyPattern,
    ) -> ProsodyScore:
        return _score_prosody(user_f0, user_times_ms, target)

    def common_errors(self, l1: str) -> ErrorPatternLib:
        return _common_errors(l1)

    async def tts_reference(self, text: str) -> bytes:
        from ...config import settings
        from ...tts.edge import synthesize as edge_synthesize

        return await edge_synthesize(text, lang="yue", voice=settings.tts_voice_yue)
