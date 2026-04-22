from __future__ import annotations

from ..base import ErrorPattern, ErrorPatternLib


_PATTERNS: dict[str, list[ErrorPattern]] = {
    "ja": [
        ErrorPattern(
            symptom="短母音を長めに、長母音を短めに発音する",
            cause="日本語の母音は常に一定長。英語の緊張・弛緩母音の区別が曖昧",
            hint="ship [ɪ] と sheep [iː] のように、長さと口の開きを両方意識する",
        ),
        ErrorPattern(
            symptom="全音節を均等なリズムで発音し、弱音節の母音弱化 (schwa) をしない",
            cause="日本語は mora-timed、英語は stress-timed。無強勢の母音は /ə/ になる",
            hint="about は『ア・バウト』ではなく [ə.ˈbaʊt]、最初の母音を弱く速く",
        ),
        ErrorPattern(
            symptom="r と l を混同（light を right と発音するなど）",
            cause="日本語の「ら行」は tap、英語の /r/ は舌をそらせる、/l/ は舌先を歯茎に",
            hint="/r/ は舌の根元を後ろに引く、/l/ は舌先で上顎に触れる",
        ),
    ],
    "zh": [
        ErrorPattern(
            symptom="Use Chinese tones on English words (rising on any 'important' syllable)",
            cause="Chinese is tonal; stress-vs-tone distinction isn't intuitive",
            hint="In English, 'stress' = longer + louder + slightly higher, not a specific pitch shape",
        ),
        ErrorPattern(
            symptom="Final consonants get a vowel attached (e.g., 'book' → 'book-uh')",
            cause="Mandarin syllables end in vowel or -n/-ng only; no other final consonants",
            hint="End the word crisply — stop the airflow without adding a vowel after",
        ),
        ErrorPattern(
            symptom="/v/ pronounced as /w/ (very → wery)",
            cause="Mandarin lacks /v/",
            hint="Touch upper teeth to lower lip and blow — like 'f' but voiced",
        ),
    ],
}


def common_errors(l1: str) -> ErrorPatternLib:
    return ErrorPatternLib(l1=l1, l2="en", patterns=_PATTERNS.get(l1, []))
