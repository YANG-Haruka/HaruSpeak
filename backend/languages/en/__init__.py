from __future__ import annotations

from .module import EnglishModule
from ..registry import register_language

register_language(EnglishModule())

__all__ = ["EnglishModule"]
