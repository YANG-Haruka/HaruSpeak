from __future__ import annotations

from ..base import ErrorPattern, ErrorPatternLib


_PATTERNS: dict[str, list[ErrorPattern]] = {
    "ja": [
        ErrorPattern(
            symptom="声調をすべてフラットに発音する（特に T2/T3 の上昇が弱い）",
            cause="日本語はピッチアクセント、中国語は声調言語。単語レベルの音高変化に慣れない",
            hint="T2 は「え？」の語末上昇のように、T3 は「はぁ…」の溜めのように意識",
        ),
        ErrorPattern(
            symptom="zh / ch / sh を清音化して日本語の「す/ち/し」に近い発音にする",
            cause="そり舌音（卷舌）が日本語に無い",
            hint="舌先を少し上に巻いて、上顎の硬口蓋あたりで発音する",
        ),
        ErrorPattern(
            symptom="-in / -ing の区別をつけない",
            cause="日本語では鼻母音の違いが語彙対立しない",
            hint="-in は舌先を歯茎に、-ing は舌の後ろを軟口蓋に",
        ),
    ],
    "en": [
        ErrorPattern(
            symptom="All syllables pronounced with English stress (loud=heavy syllable)",
            cause="Chinese tone is pitch only, not loudness; mapping stress→tone fails",
            hint="Keep loudness even; vary only pitch height and direction",
        ),
        ErrorPattern(
            symptom="T3 (falling-rising) pronounced as a simple low tone",
            cause="English has no equivalent to T3's U-shape",
            hint="Dip down first, then lift back up — like saying 'huh?' reluctantly",
        ),
        ErrorPattern(
            symptom="ü sounds (like in 绿 lǜ) pronounced as /u/",
            cause="English lacks the front rounded vowel /y/",
            hint="Round your lips as for /u/, but keep tongue position like /i/",
        ),
    ],
}


def common_errors(l1: str) -> ErrorPatternLib:
    return ErrorPatternLib(l1=l1, l2="zh", patterns=_PATTERNS.get(l1, []))
