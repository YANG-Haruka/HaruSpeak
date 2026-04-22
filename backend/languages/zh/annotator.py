"""Chinese annotator — per-hanzi pinyin with tone marks.

Non-hanzi characters (digits, punctuation, latin) are emitted as tokens
with reading=None so the frontend skips <ruby> for them.
"""
from __future__ import annotations

from ..base import AnnotatedText, Token


def _is_hanzi(s: str) -> bool:
    """True iff `s` is non-empty and every character is a CJK ideograph."""
    if not s:
        return False
    for ch in s:
        cp = ord(ch)
        if not (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF):
            return False
    return True


def annotate(text: str) -> AnnotatedText:
    try:
        from pypinyin import Style, pinyin  # type: ignore
    except ImportError:
        return AnnotatedText(language="zh", tokens=[Token(surface=text)])

    tokens: list[Token] = []
    buf: list[str] = []

    for ch in text:
        if _is_hanzi(ch):
            if buf:
                tokens.append(Token(surface="".join(buf)))
                buf = []
            py = pinyin(ch, style=Style.TONE, errors="ignore")
            reading = py[0][0] if py and py[0] else None
            tokens.append(Token(surface=ch, reading=reading))
        else:
            buf.append(ch)

    if buf:
        tokens.append(Token(surface="".join(buf)))

    if not tokens:
        tokens = [Token(surface=text)]
    return AnnotatedText(language="zh", tokens=tokens)
