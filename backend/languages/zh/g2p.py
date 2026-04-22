"""Chinese G2P via pypinyin + jieba for segmentation."""
from __future__ import annotations

from ..base import Phoneme


def g2p(text: str) -> list[Phoneme]:
    try:
        from pypinyin import Style, pinyin  # type: ignore
    except ImportError:
        return []
    # TONE3 → 'ma1', 'ma2', etc.; neutral tone = 'ma5'
    syllables = pinyin(text, style=Style.TONE3, neutral_tone_with_five=True, errors="ignore")
    flat: list[Phoneme] = []
    for group in syllables:
        for s in group:
            if s:
                flat.append(Phoneme(symbol=s))
    return flat
