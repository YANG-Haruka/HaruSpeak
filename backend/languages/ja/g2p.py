"""Japanese G2P via pyopenjtalk.

pyopenjtalk exposes `run_frontend(text)` which returns NJD features
including mora-level phoneme info. We flatten to our Phoneme dataclass.
"""
from __future__ import annotations

from ..base import Phoneme


def g2p(text: str) -> list[Phoneme]:
    """Convert Japanese text to a phoneme sequence.

    Falls back to an empty list if pyopenjtalk is not installed (the env
    won't have it during unit-tests without compile toolchain).
    """
    try:
        import pyopenjtalk
    except ImportError:
        return []

    # run_frontend returns list of NJD features; label alternative gives raw phonemes.
    # pyopenjtalk.g2p returns space-separated phonemes.
    phoneme_str = pyopenjtalk.g2p(text, kana=False)
    if not phoneme_str:
        return []
    return [Phoneme(symbol=p) for p in phoneme_str.split() if p]
