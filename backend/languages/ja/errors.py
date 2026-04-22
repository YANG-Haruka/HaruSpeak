"""Common L1→ja error patterns.

These feed into the LLM improvement-feedback prompt so the model can
focus on mistakes specific to the learner's L1 instead of generic advice.
"""
from __future__ import annotations

from ..base import ErrorPattern, ErrorPatternLib


_PATTERNS: dict[str, list[ErrorPattern]] = {
    "zh": [
        ErrorPattern(
            symptom="「つ」を「ツー (tsu-)」ではなく「ス (su)」と発音する",
            cause="中文声母系统没有 /ts/ 塞擦音，易用 /s/ 代替",
            hint="舌尖先顶上齿龈，爆破后再摩擦，像「t→s」连起来发",
        ),
        ErrorPattern(
            symptom="アクセントがすべて平坦になる（抑揚がない）",
            cause="中文是声调语言，日语重音是相对音高，学习者往往全部打平",
            hint="HL の切り替えを意識する。箸（は↓し）と橋（は↑し）を比較練習",
        ),
        ErrorPattern(
            symptom="長音 (ー) を短く発音する",
            cause="中文无音长区别；おばさん/おばあさん 混同",
            hint="長母音は 2 モラ分の時間を確保する",
        ),
        ErrorPattern(
            symptom="促音 (っ) を無視する",
            cause="中文无促音；きた/きった 混同",
            hint="促音の位置で一拍分の無音を入れる",
        ),
    ],
    "en": [
        ErrorPattern(
            symptom="Every vowel pronounced as a short English vowel",
            cause="EN has reduced vowels (schwa); JP vowels are always full",
            hint="Japanese vowels don't reduce — say each mora clearly and equally",
        ),
        ErrorPattern(
            symptom="Strong stress instead of pitch accent",
            cause="EN is stress-timed; learners apply English stress to JP",
            hint="Replace loudness/duration stress with high/low pitch change",
        ),
        ErrorPattern(
            symptom="「ら行」pronounced as English /r/",
            cause="EN /ɹ/ has no tongue contact; JP /ɾ/ is a tap",
            hint="Tap the tongue tip lightly against the alveolar ridge, like a soft D",
        ),
    ],
}


def common_errors(l1: str) -> ErrorPatternLib:
    return ErrorPatternLib(l1=l1, l2="ja", patterns=_PATTERNS.get(l1, []))
