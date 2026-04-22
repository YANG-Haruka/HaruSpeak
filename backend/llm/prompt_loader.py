"""Load and fill markdown prompt templates from prompts/logic/."""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Repo layout: backend/llm/prompt_loader.py → parents[2] is the repo root.
_PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "logic"


def load_prompt(name: str, **kwargs: Any) -> str:
    """Load `prompts/logic/{name}.md` and format using `{var}` placeholders.

    Uses str.format_map so missing keys survive as literal `{key}`,
    which is useful for partial fills and catches typos on read.
    """
    path = _PROMPT_DIR / f"{name}.md"
    raw = path.read_text(encoding="utf-8")
    return raw.format_map(_SafeDict(kwargs))


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
