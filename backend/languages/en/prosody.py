"""English prosody = word stress + sentence intonation.

Target:
- `unit_labels` = syllables across the sentence
- `stressed_indices` = which syllables carry primary stress
- `pitch_contour` = a rough rising/falling envelope based on sentence type

Score: check whether user's peak-energy syllable locations match the
expected stressed_indices; compare sentence-final F0 slope to target.
MVP uses simple heuristics; Phase 5 can fine-tune with CMUdict stress.
"""
from __future__ import annotations

from typing import Sequence

from ..base import ProsodyPattern, ProsodyScore


def _syllable_count(word: str) -> int:
    """Crude syllable counter — good enough for prosody target length."""
    word = word.lower()
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    # Silent-e: strip a SINGLE trailing e preceded by a consonant
    # ("bake" → 1, but "coffee" keeps both syllables because -ee is a diphthong-ish pair)
    if len(word) >= 3 and word.endswith("e") and word[-2] not in vowels and count > 1:
        count -= 1
    return max(1, count)


def _detect_sentence_type(text: str) -> str:
    stripped = text.strip()
    if stripped.endswith("?"):
        # Yes/no question starts with aux/be verb; wh-question starts with wh-word
        first = stripped.split()[0].lower() if stripped.split() else ""
        if first in {"what", "where", "when", "why", "who", "whose", "whom", "which", "how"}:
            return "wh_question"
        return "yn_question"
    return "declarative"


def prosody_target(text: str) -> ProsodyPattern:
    labels: list[str] = []
    stressed: list[int] = []
    for word in text.split():
        clean = "".join(ch for ch in word if ch.isalpha() or ch == "'")
        if not clean:
            continue
        n_syl = _syllable_count(clean)
        # Naive primary stress heuristic: first syllable for nouns/verbs/adjs,
        # penult for 2+ syllable words ending in -tion/-sion/-ic/-ical
        idx = len(labels)
        for i in range(n_syl):
            labels.append(f"{clean}.{i + 1}")
        low = clean.lower()
        if n_syl >= 2 and (
            low.endswith("tion")
            or low.endswith("sion")
            or low.endswith("ic")
            or low.endswith("ical")
        ):
            stress_syl = n_syl - 2
        else:
            stress_syl = 0
        stressed.append(idx + min(stress_syl, n_syl - 1))

    # Intonation envelope: flat-ish until last 3 syllables, then rise/fall.
    stype = _detect_sentence_type(text)
    contour = [0.0] * len(labels)
    if len(contour) >= 3:
        if stype == "yn_question":
            contour[-3], contour[-2], contour[-1] = -0.5, 0.5, 1.5
        elif stype == "wh_question":
            contour[-3], contour[-2], contour[-1] = 0.5, 0.0, -0.5
        else:
            contour[-3], contour[-2], contour[-1] = 0.5, 0.0, -1.0

    return ProsodyPattern(
        language="en",
        unit_labels=labels,
        pitch_contour=contour,
        stressed_indices=stressed,
    )


def score_prosody(
    user_f0: Sequence[float],
    user_times_ms: Sequence[int],
    target: ProsodyPattern,
) -> ProsodyScore:
    n = len(target.unit_labels)
    if n == 0 or not user_f0:
        return ProsodyScore(overall=0.0, per_unit=[], unit_labels=target.unit_labels)

    chunk = max(1, len(user_f0) // n)
    bins_mean: list[float] = []
    for i in range(n):
        start = i * chunk
        end = len(user_f0) if i == n - 1 else (i + 1) * chunk
        segment = [v for v in user_f0[start:end] if v > 0]
        bins_mean.append(sum(segment) / len(segment) if segment else 0.0)

    # 1. Stress-location correctness: user's relative peaks should align with stressed_indices
    stressed_set = set(target.stressed_indices)
    valid = [b for b in bins_mean if b > 0]
    avg = sum(valid) / len(valid) if valid else 0.0
    per_unit = [100.0] * n
    diff: list[float] = []

    for i, mean in enumerate(bins_mean):
        is_stressed_target = i in stressed_set
        is_user_peak = mean > avg * 1.05 and avg > 0
        if is_stressed_target and not is_user_peak:
            per_unit[i] = 50.0
        elif not is_stressed_target and is_user_peak:
            per_unit[i] = 70.0
        diff.append((mean - avg) / max(1.0, avg))

    # 2. Intonation slope at the end (last 3 units)
    if n >= 3:
        last_three = bins_mean[-3:]
        if all(v > 0 for v in last_three):
            slope = last_three[-1] - last_three[0]
            target_slope = target.pitch_contour[-1] - target.pitch_contour[-3] if len(target.pitch_contour) >= 3 else 0.0
            # Sign agreement: both rise / both fall = ok
            if target_slope > 0.2 and slope < 0:
                per_unit[-1] = 30.0
            elif target_slope < -0.2 and slope > 0:
                per_unit[-1] = 30.0

    overall = sum(per_unit) / n
    return ProsodyScore(
        overall=overall,
        per_unit=per_unit,
        unit_labels=target.unit_labels,
        diff_curve=diff,
    )
