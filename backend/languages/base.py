"""Language module contract — every L2 plugin must implement `LanguageModule`.

The pipeline only depends on this Protocol, never on concrete language code.
Adding a new language = creating a new subdirectory and registering an instance.
"""
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from pydantic import BaseModel, Field


class Phoneme(BaseModel):
    """One phoneme in a word's pronunciation."""

    symbol: str           # IPA or language-specific phoneme (e.g., "k", "a", "sh")
    start_ms: int | None = None
    end_ms: int | None = None


class Token(BaseModel):
    """One visible unit in annotated text.

    For JP a Token is typically a word (with kanji+furigana), for ZH a hanzi
    (with pinyin), for EN a word (reading=None unless marked as new vocab).
    """

    surface: str                      # 文字表面（漢字 / 汉字 / word）
    reading: str | None = None        # 注音（hiragana / pinyin-with-tones / IPA）
    ipa: str | None = None            # 严格 IPA（可选）
    gloss: str | None = None          # 词义提示
    pos: str | None = None            # 词性
    is_new: bool = False              # 是否为用户未掌握词汇


class AnnotatedText(BaseModel):
    """Structured text with per-token annotations, ready for frontend rendering."""

    language: str                     # L2 code
    tokens: list[Token]

    @property
    def plain(self) -> str:
        return "".join(t.surface for t in self.tokens)


class ProsodyPattern(BaseModel):
    """Target prosody pattern for a text.

    The semantics differ per language:
    - JP: pitch_contour is an HL pattern per mora (0/1 per mora)
    - ZH: tones is a list of tone classes (1..5) per syllable, pitch_contour is F0 template
    - EN: stressed_indices marks stressed syllables, pitch_contour is intonation envelope
    """

    language: str
    unit_labels: list[str]            # moras / syllables / syllables-of-words
    pitch_contour: list[float] = Field(default_factory=list)   # normalized F0, semitones
    tones: list[int] = Field(default_factory=list)             # ZH only
    stressed_indices: list[int] = Field(default_factory=list)  # EN only


class ProsodyScore(BaseModel):
    """Scored prosody comparison user-vs-target."""

    overall: float                    # 0-100
    per_unit: list[float]             # 0-100 per mora/syllable
    unit_labels: list[str]
    diff_curve: list[float] = Field(default_factory=list)   # user - target, semitones
    notes: list[str] = Field(default_factory=list)          # "mora 3: 上昇が足りない"


class ErrorPattern(BaseModel):
    """One typical L1→L2 pronunciation or grammar mistake pattern."""

    symptom: str                      # what the learner does wrong
    cause: str                        # L1 interference explanation
    hint: str                         # short corrective hint, in L1


class ErrorPatternLib(BaseModel):
    l1: str
    l2: str
    patterns: list[ErrorPattern]


@runtime_checkable
class LanguageModule(Protocol):
    """The plug-in contract every L2 must satisfy.

    Keep method signatures minimal and pure — anything depending on I/O
    (like TTS HTTP calls) should be async and defined in each module.
    """

    code: str
    display_names: dict[str, str]
    # Unit kind for the language: "mora" (ja) / "syllable" (zh) / "syllable-of-word" (en)
    unit_kind: str

    def g2p(self, text: str) -> list[Phoneme]: ...
    def annotate(self, text: str) -> AnnotatedText: ...
    def prosody_target(self, text: str) -> ProsodyPattern: ...
    def score_prosody(
        self,
        user_f0: Sequence[float],
        user_times_ms: Sequence[int],
        target: ProsodyPattern,
    ) -> ProsodyScore: ...

    def common_errors(self, l1: str) -> ErrorPatternLib: ...

    # I/O-bound helpers are awaitable so different backends can plug in
    async def tts_reference(self, text: str) -> bytes: ...
