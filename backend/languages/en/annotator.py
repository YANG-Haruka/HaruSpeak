"""English annotator — no furigana-style reading.

Per Haru's requirement, English doesn't need inline phonetic annotation.
We still mark rare/difficult words as is_new=True and attach IPA so the
frontend can show a tooltip on hover.
"""
from __future__ import annotations

from ..base import AnnotatedText, Token
from .common_words import COMMON_WORDS


def _split(text: str) -> list[tuple[str, bool]]:
    """Split text into (chunk, is_word) pieces preserving punctuation."""
    out: list[tuple[str, bool]] = []
    buf: list[str] = []

    def flush_word():
        if buf:
            out.append(("".join(buf), True))
            buf.clear()

    for ch in text:
        if ch.isalpha() or ch == "'":
            buf.append(ch)
        else:
            flush_word()
            out.append((ch, False))
    flush_word()
    return out


def _ipa_for(word: str) -> str | None:
    try:
        from phonemizer import phonemize  # type: ignore
    except ImportError:
        return None
    try:
        return phonemize(word, language="en-us", backend="espeak", strip=True, njobs=1).strip()
    except Exception:
        return None


def annotate(text: str) -> AnnotatedText:
    tokens: list[Token] = []
    for chunk, is_word in _split(text):
        if not is_word:
            tokens.append(Token(surface=chunk))
            continue
        lower = chunk.lower()
        is_new = lower not in COMMON_WORDS
        ipa = _ipa_for(chunk) if is_new else None
        tokens.append(Token(surface=chunk, is_new=is_new, ipa=ipa))
    if not tokens:
        tokens = [Token(surface=text)]
    return AnnotatedText(language="en", tokens=tokens)
