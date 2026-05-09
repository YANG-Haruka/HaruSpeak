"""Cantonese prosody = 6-tone system (modern HK Cantonese).

Tones (Jyutping numbers):
  1 — high level    (55) or high falling (53)
  2 — mid rising    (35 / 25)
  3 — mid level     (33)
  4 — low falling   (21 / 11)
  5 — low rising    (23)
  6 — low level     (22)

We collapse the high level / high falling allophones of T1 into the
high-level template; that's the dominant HK realization.

Confusable pairs (common learner mistakes):
  T2 ↔ T5  (both have rising elements)
  T3 ↔ T6  (both mid/low level, distinguishable mainly by register)
  T1 ↔ T3  (both level — register difference)
"""
from __future__ import annotations

from typing import Sequence

from ..base import ProsodyPattern, ProsodyScore


_TONE_TEMPLATES: dict[int, list[float]] = {
    1: [5.0, 5.0, 5.0, 5.0, 5.0],   # 55  high level
    2: [2.5, 3.0, 3.5, 4.2, 5.0],   # 25  rising from mid to high
    3: [3.0, 3.0, 3.0, 3.0, 3.0],   # 33  mid level
    4: [2.0, 1.7, 1.4, 1.2, 1.0],   # 21  falling
    5: [2.0, 2.2, 2.5, 2.8, 3.2],   # 23  low rising
    6: [2.2, 2.2, 2.2, 2.2, 2.2],   # 22  low level
}


def _extract_tones(text: str) -> tuple[list[str], list[int]]:
    try:
        import pycantonese as pc  # type: ignore
    except ImportError:
        return [], []

    labels: list[str] = []
    tones: list[int] = []
    for chunk, jp in pc.characters_to_jyutping(text):
        if not jp:
            continue
        try:
            parsed = pc.parse_jyutping(jp)
        except Exception:
            continue
        for syl in parsed:
            label = f"{syl.onset}{syl.nucleus}{syl.coda}"
            labels.append(label)
            try:
                tones.append(int(syl.tone))
            except (TypeError, ValueError):
                tones.append(3)
    return labels, tones


def prosody_target(text: str) -> ProsodyPattern:
    labels, tones = _extract_tones(text)
    contour: list[float] = []
    for t in tones:
        contour.extend(_TONE_TEMPLATES.get(t, _TONE_TEMPLATES[3]))
    return ProsodyPattern(
        language="yue",
        unit_labels=labels,
        pitch_contour=contour,
        tones=tones,
    )


def _classify_user_tone(syllable_f0: Sequence[float]) -> int:
    vals = [v for v in syllable_f0 if v > 0]
    if not vals:
        return 3
    import statistics

    mean = statistics.mean(vals)
    norm = [(v - mean) / max(1.0, abs(mean) * 0.15) + 3.0 for v in vals]
    n = len(norm)
    if n < 5:
        return 3
    idx = [int(i * (n - 1) / 4) for i in range(5)]
    user_shape = [norm[i] for i in idx]

    best_tone = 3
    best_err = float("inf")
    for t, template in _TONE_TEMPLATES.items():
        err = sum((u - tgt) ** 2 for u, tgt in zip(user_shape, template))
        if err < best_err:
            best_err = err
            best_tone = t
    return best_tone


def _confusable(a: int, b: int) -> bool:
    pairs = {(2, 5), (5, 2), (3, 6), (6, 3), (1, 3), (3, 1), (4, 6), (6, 4)}
    return (a, b) in pairs


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
