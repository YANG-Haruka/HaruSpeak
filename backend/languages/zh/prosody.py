"""Chinese prosody = per-syllable tones.

Target: a tone class (1..5; 5 = neutral) for each syllable, plus a
canonical F0 template per tone (normalized 0-1 over syllable duration).

Score: for each user syllable, we (a) compare the F0 contour shape to
each tone template and (b) pick the best-matching tone, giving full
credit if it matches target, partial if confusable (2/3 neighbors), zero
otherwise. MVP uses a simple shape-based heuristic without DTW.
"""
from __future__ import annotations

from typing import Sequence

from ..base import ProsodyPattern, ProsodyScore


# Canonical 5-point F0 skeleton per tone (relative, higher = higher pitch).
_TONE_TEMPLATES: dict[int, list[float]] = {
    1: [5.0, 5.0, 5.0, 5.0, 5.0],   # 55  high level
    2: [3.5, 3.8, 4.2, 4.7, 5.0],   # 35  rising
    3: [2.5, 1.5, 1.5, 2.5, 4.0],   # 214 dipping
    4: [5.0, 4.2, 3.3, 2.5, 1.0],   # 51  falling
    5: [3.0, 2.8, 2.6, 2.5, 2.4],   # neutral, mid-low short
}


def _apply_tone_sandhi(tones: list[int]) -> list[int]:
    """Mandarin 3-3 sandhi: two consecutive T3 → first becomes T2."""
    out = list(tones)
    for i in range(len(out) - 1):
        if out[i] == 3 and out[i + 1] == 3:
            out[i] = 2
    return out


def _extract_tones(text: str) -> tuple[list[str], list[int]]:
    try:
        from pypinyin import Style, pinyin  # type: ignore
    except ImportError:
        return [], []

    py = pinyin(text, style=Style.TONE3, neutral_tone_with_five=True, errors="ignore")
    labels: list[str] = []
    tones: list[int] = []
    for group in py:
        for s in group:
            if not s:
                continue
            # Last char is the digit tone if present
            if s and s[-1].isdigit():
                tone = int(s[-1])
                label = s[:-1]
            else:
                tone = 5
                label = s
            labels.append(label)
            tones.append(tone)
    return labels, _apply_tone_sandhi(tones)


def prosody_target(text: str) -> ProsodyPattern:
    labels, tones = _extract_tones(text)
    contour: list[float] = []
    for t in tones:
        contour.extend(_TONE_TEMPLATES.get(t, _TONE_TEMPLATES[5]))
    return ProsodyPattern(
        language="zh",
        unit_labels=labels,
        pitch_contour=contour,
        tones=tones,
    )


def _classify_user_tone(syllable_f0: Sequence[float]) -> int:
    """Return the tone class that best matches the user's F0 shape."""
    vals = [v for v in syllable_f0 if v > 0]
    if not vals:
        return 5
    import statistics

    mean = statistics.mean(vals)
    # Normalize to 0-10 range relative to mean
    norm = [(v - mean) / max(1.0, abs(mean) * 0.15) + 3.0 for v in vals]
    # Pick 5 evenly spaced points
    n = len(norm)
    if n < 5:
        return 5
    idx = [int(i * (n - 1) / 4) for i in range(5)]
    user_shape = [norm[i] for i in idx]

    best_tone = 5
    best_err = float("inf")
    for t, template in _TONE_TEMPLATES.items():
        err = sum((u - tgt) ** 2 for u, tgt in zip(user_shape, template))
        if err < best_err:
            best_err = err
            best_tone = t
    return best_tone


def score_prosody(
    user_f0: Sequence[float],
    user_times_ms: Sequence[int],
    target: ProsodyPattern,
) -> ProsodyScore:
    n = len(target.tones)
    if n == 0 or not user_f0:
        return ProsodyScore(overall=0.0, per_unit=[], unit_labels=target.unit_labels)

    chunk = max(1, len(user_f0) // n)
    per_unit: list[float] = []
    diff: list[float] = []
    for i, target_tone in enumerate(target.tones):
        start = i * chunk
        end = len(user_f0) if i == n - 1 else (i + 1) * chunk
        predicted = _classify_user_tone(user_f0[start:end])
        if predicted == target_tone:
            score = 100.0
        elif _confusable(predicted, target_tone):
            score = 55.0
        else:
            score = 10.0
        per_unit.append(score)
        diff.append(float(predicted - target_tone))

    overall = sum(per_unit) / n if n else 0.0
    return ProsodyScore(
        overall=overall,
        per_unit=per_unit,
        unit_labels=target.unit_labels,
        diff_curve=diff,
    )


def _confusable(a: int, b: int) -> bool:
    """Known confusions: T2↔T3 (both have rising elements), T4↔T1 (both strong)."""
    pairs = {(2, 3), (3, 2), (1, 4), (4, 1), (5, 3), (3, 5)}
    return (a, b) in pairs
