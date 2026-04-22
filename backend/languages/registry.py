"""Registry for dynamically loading LanguageModule instances.

Each language subpackage registers itself on import (see ja/__init__.py).
Languages not yet implemented raise NotImplementedError at call time, so
the Protocol surface still passes static checks.
"""
from __future__ import annotations

from typing import Iterable

from .base import LanguageModule

_REGISTRY: dict[str, LanguageModule] = {}


def register_language(module: LanguageModule) -> None:
    if not hasattr(module, "code") or not module.code:
        raise ValueError("LanguageModule must expose a non-empty `code`")
    _REGISTRY[module.code] = module


def get_language(code: str) -> LanguageModule:
    if code not in _REGISTRY:
        raise KeyError(
            f"Language '{code}' not registered. "
            f"Available: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[code]


def list_languages() -> list[str]:
    """All languages whose module has been imported, including stubs."""
    return sorted(_REGISTRY.keys())


def ensure_loaded(codes: Iterable[str]) -> None:
    """Import language packages so they register themselves.

    Separate function so frontend can ask about available languages without
    tripping NotImplementedError at import time.
    """
    import importlib

    for code in codes:
        try:
            importlib.import_module(f"backend.languages.{code}")
        except ImportError:
            importlib.import_module(f"languages.{code}")  # running from backend/
