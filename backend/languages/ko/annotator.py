"""Korean annotator — hangul is already phonetic, so no per-syllable reading.

Every hangul block becomes its own Token (matching `unit_kind = "syllable"`),
which lets the frontend colour per-syllable like Chinese. Punctuation and
spaces are passed through untouched.
"""
from __future__ import annotations

from ..base import AnnotatedText, Token


def _is_hangul_syllable(ch: str) -> bool:
    return "가" <= ch <= "힣"


def annotate(text: str) -> AnnotatedText:
    tokens: list[Token] = []
    buf: list[str] = []

    def flush_non_hangul() -> None:
        if buf:
            tokens.append(Token(surface="".join(buf)))
            buf.clear()

    for ch in text:
        if _is_hangul_syllable(ch):
            flush_non_hangul()
            tokens.append(Token(surface=ch))
        else:
            buf.append(ch)
    flush_non_hangul()

    if not tokens:
        tokens = [Token(surface=text)]
    return AnnotatedText(language="ko", tokens=tokens)
