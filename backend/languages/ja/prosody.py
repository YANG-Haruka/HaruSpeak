"""Japanese prosody = pitch accent.

Accent pattern is a per-mora HL sequence derived from pyopenjtalk's NJD
accent field:
- acc == 0  → heibangata (平板): first mora L, rest H
- acc == 1  → atamadaka (頭高):  first mora H, rest L
- acc == n>1 → nakadaka/odaka:    L H…H (up to n-th mora) then L

The user F0 curve is compared to this target via DTW after z-score
normalization in semitones. We score 0-100 per mora based on how close
the user curve's HL binarization matches target.
"""
from __future__ import annotations

import math
from typing import Sequence

from ..base import ProsodyPattern, ProsodyScore


def _extract_accent(text: str) -> tuple[list[str], list[int]]:
    """Return (mora_labels, hl_pattern). hl is 0=L, 1=H per mora.

    Uses pyopenjtalk NJD features. Accent is applied per accent-phrase,
    but for MVP we concatenate all phrases into one pattern.
    """
    try:
        import pyopenjtalk
    except ImportError:
        return [], []

    features = pyopenjtalk.run_frontend(text)
    mora_labels: list[str] = []
    hl: list[int] = []

    for feat in features:
        if isinstance(feat, dict):
            pron = feat.get("pron", "")
            acc = feat.get("acc", 0)
            mora_size = feat.get("mora_size", len(pron))
        else:
            pron = getattr(feat, "pron", "") or ""
            acc = getattr(feat, "acc", 0) or 0
            mora_size = getattr(feat, "mora_size", len(pron)) or len(pron)

        if mora_size <= 0 or not pron:
            continue

        # Split pron katakana into moras — naive: one char per mora
        # (pyopenjtalk actually exposes mora boundaries; this approximation
        # is fine for scoring, not for ML training)
        moras = list(pron)[:mora_size]
        mora_labels.extend(moras)

        phrase_hl = _accent_to_hl(acc, mora_size)
        hl.extend(phrase_hl)

    return mora_labels, hl


def _accent_to_hl(acc: int, n: int) -> list[int]:
    """Build HL pattern of length n for accent core `acc`.

    - acc=0: [L, H, H, ...H]
    - acc=1: [H, L, L, ...L]
    - acc=k (1<k<=n): [L, H, ...H (up to k-th), L, L, ...]
    """
    if n <= 0:
        return []
    if acc == 0:
        return [0] + [1] * (n - 1)
    if acc == 1:
        return [1] + [0] * (n - 1)
    # 1 < acc <= n
    out = [0]
    for i in range(1, n):
        if i < acc:
            out.append(1)
        else:
            out.append(0)
    return out


def prosody_target(text: str) -> ProsodyPattern:
    labels, hl = _extract_accent(text)
    # pitch_contour in semitones: L=0, H=+2 as a reasonable target delta
    contour = [float(h) * 2.0 for h in hl]
    return ProsodyPattern(
        language="ja",
        unit_labels=labels,
        pitch_contour=contour,
    )


def _mean(xs: Sequence[float]) -> float:
    xs = [x for x in xs if x > 0 and not math.isnan(x)]
    if not xs:
        return 0.0
    return sum(xs) / len(xs)


def _hz_to_semitones(f0: Sequence[float], ref_hz: float) -> list[float]:
    if ref_hz <= 0:
        return [0.0] * len(f0)
    out = []
    for v in f0:
        if v <= 0 or math.isnan(v):
            out.append(0.0)
        else:
            out.append(12.0 * math.log2(v / ref_hz))
    return out


def score_prosody(
    user_f0: Sequence[float],
    user_times_ms: Sequence[int],
    target: ProsodyPattern,
) -> ProsodyScore:
    """Score user F0 against target HL pattern.

    MVP version: downsample user F0 to target mora count, compute per-mora
    relative height (above/below user's own mean), then compare bits to target.
    DTW alignment is added later when we have more real audio to tune on.
    """
    n_units = len(target.unit_labels)
    if n_units == 0 or not user_f0:
        return ProsodyScore(
            overall=0.0,
            per_unit=[],
            unit_labels=target.unit_labels,
        )

    # Bin user F0 into n_units equal-time windows
    chunk = max(1, len(user_f0) // n_units)
    bins: list[float] = []
    for i in range(n_units):
        start = i * chunk
        end = len(user_f0) if i == n_units - 1 else (i + 1) * chunk
        bins.append(_mean(user_f0[start:end]))

    ref = _mean([b for b in bins if b > 0])
    semi = _hz_to_semitones(bins, ref)

    per_unit: list[float] = []
    diff_curve: list[float] = []
    for user_st, tgt_st in zip(semi, target.pitch_contour):
        diff = user_st - tgt_st
        diff_curve.append(diff)
        # Score: within ±1 semitone → 100, falloff linear to 0 at ±6 st
        mag = abs(diff)
        if mag <= 1.0:
            per_unit.append(100.0)
        elif mag >= 6.0:
            per_unit.append(0.0)
        else:
            per_unit.append(100.0 * (6.0 - mag) / 5.0)

    overall = sum(per_unit) / len(per_unit) if per_unit else 0.0
    return ProsodyScore(
        overall=overall,
        per_unit=per_unit,
        unit_labels=target.unit_labels,
        diff_curve=diff_curve,
    )
