"""Chain-of-thought stripping helpers.

Reasoning-tuned local models (Qwen3, DeepSeek-R1, some fine-tunes) can
leak their chain-of-thought into the `content` stream in several shapes:

  1. `<think>…</think>` blocks (Qwen3 / DeepSeek-R1 native)
  2. Prose preambles like "Thinking Process: …" / "Analyze the Request:"
  3. Numbered-list reasoning: `1. **Analyze the Request:** … 2. **Translate:** …`

This module strips all three. Only used by the local LM Studio backend —
cloud models are assumed to be well-behaved and emit clean content.
"""
from __future__ import annotations

import re


_THINK_TAG_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

_PREAMBLE_HEADERS = (
    r"thinking\s+process[:：]",
    r"let\s+me\s+think",
    r"let'?s\s+think",
    r"analyze\s+the\s+request[:：]?",
    r"step[-\s]by[-\s]step[:：]?",
    r"思考(?:过程|プロセス)[:：]",
    r"让我思考",
    r"考えて(?:みます|みましょう)",
)
_THINK_PROSE_RE = re.compile(
    r"^\s*(?:\*\*)?(?:" + "|".join(_PREAMBLE_HEADERS) + r")(?:\*\*)?[\s\S]*?(?=\n\s*\n|\Z)",
    re.IGNORECASE,
)

_THINK_LIST_RE = re.compile(r"^\s*\d+\.\s*\*\*[\s\S]*?(?=\n\s*\n|\Z)")

_META_RE = re.compile(r"\b(?:Input|Task|Constraints?|Analyze)\s*[:：]", re.IGNORECASE)


def strip_thinking(text: str) -> str:
    if not text:
        return text
    cleaned = _THINK_TAG_RE.sub("", text)
    cleaned = _THINK_PROSE_RE.sub("", cleaned)
    cleaned = _THINK_LIST_RE.sub("", cleaned)
    # Single-paragraph reasoning with no blank-line terminator — keep only
    # the tail after the last "->" arrow (where many models put the answer).
    if _META_RE.search(cleaned):
        tail = cleaned.rsplit("->", 1)
        if len(tail) == 2:
            cleaned = tail[1]
    return cleaned.strip().strip('"').strip("「」『』").strip()
