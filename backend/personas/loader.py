"""Per-L2 persona loader — voices + character descriptions from prompts/personas/.

A persona bundles (voice_id, system_prompt_tail, difficulty_preference).
Used to let users pick 部長 vs 同僚 vs 後輩 for JP, e.g.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# backend/personas/loader.py → parents[2] is the repo root.
_ROOT = Path(__file__).resolve().parents[2] / "prompts" / "personas"


def list_personas(l2: str) -> list[dict[str, Any]]:
    p = _ROOT / f"{l2}.yaml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("personas", [])


def get_persona(l2: str, persona_id: str) -> dict[str, Any] | None:
    for p in list_personas(l2):
        if p.get("id") == persona_id:
            return p
    return None
