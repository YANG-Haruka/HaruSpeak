"""English G2P via phonemizer (espeak-ng backend)."""
from __future__ import annotations

from ..base import Phoneme


def g2p(text: str) -> list[Phoneme]:
    try:
        from phonemizer import phonemize  # type: ignore
    except ImportError:
        return []
    try:
        ipa = phonemize(
            text,
            language="en-us",
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            njobs=1,
        )
    except Exception:
        return []
    phonemes: list[Phoneme] = []
    for sym in ipa.split():
        for ch in sym:
            if ch.strip():
                phonemes.append(Phoneme(symbol=ch))
    return phonemes
