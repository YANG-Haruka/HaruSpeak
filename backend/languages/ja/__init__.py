from __future__ import annotations

from .annotator import annotate
from .errors import common_errors
from .g2p import g2p
from .module import JapaneseModule
from .prosody import prosody_target, score_prosody

_instance = JapaneseModule()

# Register on import
from ..registry import register_language

register_language(_instance)

__all__ = [
    "JapaneseModule",
    "annotate",
    "common_errors",
    "g2p",
    "prosody_target",
    "score_prosody",
]
