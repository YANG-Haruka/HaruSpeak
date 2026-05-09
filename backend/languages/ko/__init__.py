from __future__ import annotations

from ..registry import register_language
from .module import KoreanModule

register_language(KoreanModule())

__all__ = ["KoreanModule"]
