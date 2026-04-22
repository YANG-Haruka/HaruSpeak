"""Load scenario YAML files from prompts/scenes/.

Two tiers:
- prompts/scenes/common/*.yaml   — cross-language, declares supported L2s via `languages:`
- prompts/scenes/<l2>/*.yaml     — L2-specific cultural scenarios
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# backend/scenes/loader.py → parents[2] is the repo root.
_SCENES_ROOT = Path(__file__).resolve().parents[2] / "prompts" / "scenes"


def load_all(l2: str) -> list[dict[str, Any]]:
    """Return scenes available for a given L2."""
    out: list[dict[str, Any]] = []

    common_dir = _SCENES_ROOT / "common"
    if common_dir.is_dir():
        for p in sorted(common_dir.glob("*.yaml")):
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if not data:
                continue
            langs = data.get("languages", [])
            if l2 in langs or not langs:
                out.append({**data, "source": "common", "id": data.get("id", p.stem)})

    l2_dir = _SCENES_ROOT / l2
    if l2_dir.is_dir():
        for p in sorted(l2_dir.glob("*.yaml")):
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if not data:
                continue
            out.append({**data, "source": l2, "id": data.get("id", p.stem)})

    return out


def load_one(scene_id: str, l2: str) -> dict[str, Any] | None:
    for s in load_all(l2):
        if s["id"] == scene_id:
            return s
    return None
