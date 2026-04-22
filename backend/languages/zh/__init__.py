from __future__ import annotations

from .module import ChineseModule
from ..registry import register_language

register_language(ChineseModule())

__all__ = ["ChineseModule"]
