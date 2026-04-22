"""Japanese annotator — generate furigana for kanji-containing text.

Tries two tokenizers in order:
1. pyopenjtalk (richer, but requires MSVC on Windows to install)
2. fugashi + unidic-lite (pip-installable Windows wheels)

If both are missing we fall back to a single token with no reading.
"""
from __future__ import annotations

from ..base import AnnotatedText, Token

# Katakana→Hiragana offset (U+30A1..U+30F6 → U+3041..U+3096)
_KATA_START = 0x30A1
_KATA_END = 0x30F6
_HIRA_START = 0x3041


def _kata_to_hira(kata: str) -> str:
    out = []
    for ch in kata:
        cp = ord(ch)
        if _KATA_START <= cp <= _KATA_END:
            out.append(chr(cp - _KATA_START + _HIRA_START))
        else:
            out.append(ch)
    return "".join(out)


def _has_kanji(s: str) -> bool:
    return any(0x4E00 <= ord(ch) <= 0x9FFF for ch in s)


# Lazy-cached fugashi tagger
_tagger = None


def _fugashi_tagger():
    global _tagger
    if _tagger is not None:
        return _tagger
    try:
        from fugashi import Tagger

        _tagger = Tagger()
        return _tagger
    except Exception:
        return None


def _annotate_with_pyopenjtalk(text: str):
    try:
        import pyopenjtalk
    except ImportError:
        return None
    features = pyopenjtalk.run_frontend(text)
    tokens: list[Token] = []
    for feat in features:
        if isinstance(feat, dict):
            surface = feat.get("string", "")
            pron_kata = feat.get("pron", "")
            pos = feat.get("pos", None)
        else:
            surface = getattr(feat, "string", "") or (feat[0] if len(feat) else "")
            pron_kata = getattr(feat, "pron", "") or (feat[9] if len(feat) > 9 else "")
            pos = None
        if not surface:
            continue
        reading = None
        if _has_kanji(surface) and pron_kata:
            reading = _kata_to_hira(pron_kata)
        tokens.append(Token(surface=surface, reading=reading, pos=pos))
    return tokens or None


def _annotate_with_fugashi(text: str):
    tagger = _fugashi_tagger()
    if tagger is None:
        return None
    tokens: list[Token] = []
    for word in tagger(text):
        surface = word.surface
        if not surface:
            continue
        feat = getattr(word, "feature", None)
        reading_kata = getattr(feat, "kana", None) if feat is not None else None
        pos = getattr(feat, "pos1", None) if feat is not None else None
        reading = None
        if reading_kata and reading_kata != "*" and _has_kanji(surface):
            reading = _kata_to_hira(reading_kata)
        tokens.append(Token(surface=surface, reading=reading, pos=pos))
    return tokens or None


def annotate(text: str) -> AnnotatedText:
    """Return AnnotatedText with furigana on kanji-containing tokens."""
    tokens = _annotate_with_pyopenjtalk(text) or _annotate_with_fugashi(text)
    if not tokens:
        tokens = [Token(surface=text)]
    return AnnotatedText(language="ja", tokens=tokens)
