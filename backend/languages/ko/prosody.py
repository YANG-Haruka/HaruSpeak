"""Korean prosody = phrase-level intonation (no lexical stress, no tones).

Korean is mora-isochronous-ish but the salient learner mistake is the wrong
sentence-final contour: yes/no questions rise (-까?), wh-questions and
declaratives fall. We model that envelope and ignore per-syllable stress.
"""
from __future__ import annotations

from typing import Sequence

from ..base import ProsodyPattern, ProsodyScore


def _is_hangul_syllable(ch: str) -> bool:
    return "가" <= ch <= "힣"


def _detect_sentence_type(text: str) -> str:
    stripped = text.strip()
    if stripped.endswith("?"):
        # 까/니/요? → yes/no rise; 뭐/어디/언제/왜 → wh-question fall
        wh_markers = ("뭐", "무엇", "어디", "언제", "왜", "어떻게", "누구", "얼마")
        if any(w in stripped for w in wh_markers):
            return "wh_question"
        return "yn_question"
    return "declarative"


def prosody_target(text: str) -> ProsodyPattern:
    labels = [ch for ch in text if _is_hangul_syllable(ch)]
    n = len(labels)
    contour = [0.0] * n
    if n >= 3:
        stype = _detect_sentence_type(text)
        if stype == "yn_question":
            contour[-3], contour[-2], contour[-1] = -0.5, 0.5, 1.5
        elif stype == "wh_question":
            contour[-3], contour[-2], contour[-1] = 0.5, 0.0, -0.5
        else:
            contour[-3], contour[-2], contour[-1] = 0.5, 0.0, -1.0
    return ProsodyPattern(language="ko", unit_labels=labels, pitch_contour=contour)


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
        seg = [v for v in user_f0[start:end] if v > 0]
        bins_mean.append(sum(seg) / len(seg) if seg else 0.0)

    per_unit = [100.0] * n
    diff: list[float] = []
    valid = [b for b in bins_mean if b > 0]
    avg = sum(valid) / len(valid) if valid else 0.0
    for mean in bins_mean:
        diff.append((mean - avg) / max(1.0, avg))

    if n >= 3 and all(v > 0 for v in bins_mean[-3:]):
        last_three = bins_mean[-3:]
        slope = last_three[-1] - last_three[0]
        target_slope = target.pitch_contour[-1] - target.pitch_contour[-3]
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
