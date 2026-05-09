"""Cantonese annotator — per-hanzi Jyutping (粤拼) reading.

Mirrors the zh module's per-character pattern: each Han character gets its
own Token with a Jyutping reading, non-hanzi chunks (punctuation, digits,
spaces) collapse into a single Token with reading=None so the frontend
skips <ruby> rendering for them.

pycantonese's `characters_to_jyutping` segments multi-char idioms together
(e.g. 今日 → 'gam1jat6'). We parse those back out into per-syllable
Jyutping so per-hanzi annotation aligns with the underlying tones.
"""
from __future__ import annotations

from ..base import AnnotatedText, Token


def _is_hanzi(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF


def _split_jp(jp: str) -> list[str]:
    """Split a multi-syllable Jyutping string into per-syllable pieces."""
    try:
        import pycantonese as pc  # type: ignore

        parsed = pc.parse_jyutping(jp)
    except Exception:
        return [jp]
    return [f"{s.onset}{s.nucleus}{s.coda}{s.tone}" for s in parsed]


def annotate(text: str) -> AnnotatedText:
    try:
        import pycantonese as pc  # type: ignore
    except ImportError:
        return AnnotatedText(language="yue", tokens=[Token(surface=text)])

    tokens: list[Token] = []
    buf_non_hanzi: list[str] = []

    def flush_non_hanzi() -> None:
        if buf_non_hanzi:
            tokens.append(Token(surface="".join(buf_non_hanzi)))
            buf_non_hanzi.clear()

    for chunk, jp in pc.characters_to_jyutping(text):
        if not jp:
            buf_non_hanzi.append(chunk)
            continue
        flush_non_hanzi()
        chars = list(chunk)
        readings = _split_jp(jp)
        # Defensive: if the segmentation lengths disagree (rare for hanzi),
        # fall back to the whole chunk as a single token rather than crashing.
        if len(chars) == len(readings):
            for ch, r in zip(chars, readings):
                if _is_hanzi(ch):
                    tokens.append(Token(surface=ch, reading=r))
                else:
                    tokens.append(Token(surface=ch))
        else:
            tokens.append(Token(surface=chunk, reading=jp))

    flush_non_hanzi()
    if not tokens:
        tokens = [Token(surface=text)]
    return AnnotatedText(language="yue", tokens=tokens)
