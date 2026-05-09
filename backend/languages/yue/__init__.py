from __future__ import annotations

from ..registry import register_language
from .module import CantoneseModule

register_language(CantoneseModule())

__all__ = ["CantoneseModule"]
