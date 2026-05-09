"""Cantonese G2P via pycantonese — Jyutping per syllable.

Returns the full Jyutping syllable (e.g. 'nei5', 'hou2') as the phoneme
symbol. Tones are part of the symbol via the trailing digit, mirroring
how the zh module emits `ma1`, `ma2`, etc.
"""
from __future__ import annotations

from ..base import Phoneme


def g2p(text: str) -> list[Phoneme]:
    try:
        import pycantonese as pc  # type: ignore
    except ImportError:
        return []
    out: list[Phoneme] = []
    for chunk, jp in pc.characters_to_jyutping(text):
        if not jp:
            continue
        try:
            parsed = pc.parse_jyutping(jp)
        except Exception:
            continue
        for syl in parsed:
            symbol = f"{syl.onset}{syl.nucleus}{syl.coda}{syl.tone}"
            out.append(Phoneme(symbol=symbol))
    return out
