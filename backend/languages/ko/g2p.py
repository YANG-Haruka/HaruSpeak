"""Korean G2P via phonemizer (espeak-ng backend, language=ko).

Hangul is featural, so we *could* decompose to jamo directly, but reusing
espeak keeps the dependency surface identical to en/fr/es/de.
"""
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
            language="ko",
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            njobs=1,
        )
    except Exception:
        return []
    out: list[Phoneme] = []
    for sym in ipa.split():
        for ch in sym:
            if ch.strip():
                out.append(Phoneme(symbol=ch))
    return out
