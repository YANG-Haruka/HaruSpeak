"""Conversation pipeline — STT → LLM → annotate → TTS.

The pipeline is language-agnostic; the L2 LanguageModule is injected
and used for annotation + TTS reference audio.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any

from pydantic import BaseModel

from ..languages import AnnotatedText, LanguageModule, get_language
from ..llm.base import LLMBackend
from ..llm.prompt_loader import load_prompt
from ..stt.base import STTBackend, Transcript


_LANG_NAME = {"ja": "Japanese", "zh": "Chinese", "en": "English"}


def _extract_json_array(raw: str) -> list[Any]:
    """Robustly pull a JSON array out of an LLM reply.

    Handles: pure JSON, markdown-fenced JSON, JSON with a leading preamble,
    single/double-quoted variants with a retry.
    """
    if not raw:
        return []
    # Strip markdown code fences (```json ... ``` or plain ```)
    m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", raw)
    candidate = m.group(1) if m else None
    # Or first top-level JSON array in the reply
    if not candidate:
        m = re.search(r"\[[\s\S]*\]", raw)
        candidate = m.group(0) if m else None
    if not candidate:
        return []
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Loose fallback: replace single quotes with double quotes
        try:
            return json.loads(candidate.replace("'", '"'))
        except json.JSONDecodeError:
            return []


class ConversationTurn(BaseModel):
    role: str            # "user" | "assistant"
    text: str
    annotated: AnnotatedText | None = None
    translation: str | None = None       # translated into L1
    audio_mime: str | None = None        # e.g., "audio/mpeg" for edge-tts MP3
    audio_b64: str | None = None         # base64-encoded audio bytes


class ReplySuggestion(BaseModel):
    tier: str                        # "short" | "polite" | "detailed"
    text: str
    annotated: AnnotatedText


class TurnResult(BaseModel):
    transcript: Transcript
    ai_reply: ConversationTurn
    suggestions: list[ReplySuggestion]


class ConversationPipeline:
    def __init__(
        self,
        stt: STTBackend,
        llm: LLMBackend,
        l1: str,
        l2: str,
        scene: dict[str, Any],
        level: str = "B1",
        persona: str = "native speaker",
    ) -> None:
        self.stt = stt
        self.llm = llm
        self.l1 = l1
        self.l2 = l2
        self.scene = scene
        self.level = level
        self.persona = persona
        self.lang: LanguageModule = get_language(l2)
        self._history: list[ConversationTurn] = []

    def _system_prompt(self) -> str:
        err_lib = self.lang.common_errors(self.l1)
        hints = "\n".join(f"- {p.symptom} — {p.hint}" for p in err_lib.patterns) or "(none)"
        return load_prompt(
            "conversation",
            persona=self.persona,
            l1=self.l1,
            l2=self.l2,
            l1_name=_LANG_NAME.get(self.l1, self.l1),
            l2_name=_LANG_NAME.get(self.l2, self.l2),
            level=self.level,
            scene_description=self.scene.get("description", self.scene.get("title", "")),
            l1_l2_error_hints=hints,
        )

    def _messages(self, user_text: str) -> list[dict]:
        msgs = [{"role": t.role, "content": t.text} for t in self._history]
        msgs.append({"role": "user", "content": user_text})
        return msgs

    async def stream_user_turn(self, audio_bytes: bytes, emit) -> None:
        """Handle a user turn; emit events as each stage completes.

        `emit(event_type: str, payload: dict)` awaited by caller.
        Stages (arrival order is as-completed, not strictly sequential):
            transcript → ai_text_delta* → ai_text → (ai_audio | ai_translation | suggestions) → turn_done
        """
        transcript = await self.stt.transcribe(audio_bytes, language=self.l2)
        user_turn = ConversationTurn(
            role="user",
            text=transcript.text,
            annotated=self.lang.annotate(transcript.text),
        )
        self._history.append(user_turn)
        await emit("transcript", {"transcript": transcript.model_dump()})

        # LLM main reply — stream token-by-token so user sees text appearing
        # while the model is still generating (Grok/ChatGPT-style).
        # max_tokens is generous so reasoning-tuned local models (Qwen3,
        # DeepSeek-R1) still have budget for actual content after their
        # chain-of-thought; if finish_reason=length we fall back to complete().
        reply_text = ""
        try:
            async for chunk in self.llm.stream(
                system=self._system_prompt(),
                messages=self._messages(transcript.text),
                max_tokens=2048,
            ):
                if not chunk:
                    continue
                reply_text += chunk
                await emit("ai_text_delta", {"delta": chunk})
        except Exception as e:
            print(f"[llm.stream] failed, falling back to complete(): {e}")
        # If stream yielded nothing (common with reasoning models that blow
        # their token budget inside <think>), re-run as a blocking complete
        # with a big budget so the user still gets a reply.
        if not reply_text.strip():
            reply_text = await self.llm.complete(
                system=self._system_prompt(),
                messages=self._messages(transcript.text),
                max_tokens=2048,
            )

        # Final annotated version (tokenizer + furigana / pinyin) arrives after
        # the whole string is known — the streaming delta frames above already
        # showed plain text to the user.
        annotated = self.lang.annotate(reply_text)
        await emit(
            "ai_text",
            {"text": reply_text, "annotated": annotated.model_dump()},
        )

        ai_turn = ConversationTurn(
            role="assistant",
            text=reply_text,
            annotated=annotated,
        )
        self._history.append(ai_turn)

        # Fan-out: each coroutine emits its own event as soon as it finishes.
        async def _tts_and_emit() -> None:
            audio = await self.lang.tts_reference(reply_text)
            ai_turn.audio_mime = "audio/mpeg" if audio else None
            ai_turn.audio_b64 = (
                base64.b64encode(audio).decode("ascii") if audio else None
            )
            await emit(
                "ai_audio",
                {"audio_mime": ai_turn.audio_mime, "audio_b64": ai_turn.audio_b64},
            )

        async def _translate_and_emit() -> None:
            tr = await self._translate(reply_text)
            ai_turn.translation = tr
            await emit("ai_translation", {"translation": tr})

        async def _suggestions_and_emit() -> None:
            sugg = await self._generate_suggestions(reply_text)
            await emit(
                "suggestions",
                {"suggestions": [s.model_dump() for s in sugg]},
            )

        # return_exceptions=True so one failing stage doesn't cancel the others.
        results = await asyncio.gather(
            _tts_and_emit(),
            _translate_and_emit(),
            _suggestions_and_emit(),
            return_exceptions=True,
        )
        for stage, result in zip(("tts", "translate", "suggestions"), results):
            if isinstance(result, Exception):
                print(f"[{stage}] failed: {type(result).__name__}: {result}")
        await emit("turn_done", {})

    async def generate_suggestions(self, ai_last: str) -> list[ReplySuggestion]:
        """Public entry so main.py can also generate suggestions for the opening line."""
        return await self._generate_suggestions(ai_last)

    async def _generate_suggestions(self, ai_last: str) -> list[ReplySuggestion]:
        level_down, level_up = self._bracket(self.level)
        prompt = load_prompt(
            "reply_suggest",
            l2_name=_LANG_NAME.get(self.l2, self.l2),
            ai_last_message=ai_last,
            level=self.level,
            level_minus_one=level_down,
            level_plus_one=level_up,
            scene_description=self.scene.get("description", self.scene.get("title", "casual conversation")),
            persona=self.persona,
        )
        suggestions_schema = {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tier": {"type": "string", "enum": ["short", "polite", "detailed"]},
                            "text": {"type": "string"},
                        },
                        "required": ["tier", "text"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 3,
                },
            },
            "required": ["suggestions"],
            "additionalProperties": False,
        }
        raw = await self.llm.complete(
            system="Return a JSON object with a `suggestions` array.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "reply_suggestions", "schema": suggestions_schema},
            },
        )
        # Response is `{"suggestions": [...]}` under json_schema mode; unwrap.
        items: list[Any] = []
        try:
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict) and isinstance(parsed.get("suggestions"), list):
                items = parsed["suggestions"]
        except json.JSONDecodeError:
            # Legacy models that ignore the schema may still emit a bare array
            items = _extract_json_array(raw)
        if not items:
            print(f"[suggestions] could not parse LLM output: {raw[:200]!r}")
            return []
        out: list[ReplySuggestion] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = item.get("text", "")
            if not text:
                continue
            out.append(
                ReplySuggestion(
                    tier=item.get("tier", "polite"),
                    text=text,
                    annotated=self.lang.annotate(text),
                )
            )
        return out

    async def _translate(self, text: str) -> str:
        """Translate L2 text to L1 via a fast LLM call.

        We use JSON mode — reasoning-tuned local models treat a prose
        "no reasoning please" instruction as something to reason about,
        but a structured JSON schema is harder to escape. Falls back to
        plain-text parsing if the model's JSON is malformed.
        """
        if self.l1 == self.l2 or not text.strip():
            return ""
        l1_name = _LANG_NAME.get(self.l1, self.l1)
        l2_name = _LANG_NAME.get(self.l2, self.l2)
        schema = {
            "type": "object",
            "properties": {"t": {"type": "string"}},
            "required": ["t"],
            "additionalProperties": False,
        }
        try:
            raw = await self.llm.complete(
                system=f"Translate {l2_name} to {l1_name}.",
                messages=[{"role": "user", "content": text}],
                max_tokens=400,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "translation", "schema": schema},
                },
            )
        except Exception as e:
            print(f"[translate] failed: {e}")
            return ""
        raw = raw.strip()
        # Primary path: parse JSON
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                for k in ("t", "translation", "text", "output"):
                    v = obj.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip().strip('"').strip("「」『』").strip()
        except json.JSONDecodeError:
            pass
        # Fallback: extract first JSON object with a string value anywhere
        m = re.search(r'\{[^{}]*"[^"]+"\s*:\s*"([^"]+)"[^{}]*\}', raw)
        if m:
            return m.group(1).strip()
        # Last resort: the thinking-stripped raw text
        return raw.strip().strip('"').strip("「」『』").strip()

    @staticmethod
    def _bracket(level: str) -> tuple[str, str]:
        order = ["A1", "A2", "B1", "B2", "C1", "C2"]
        if level in order:
            idx = order.index(level)
            lo = order[max(0, idx - 1)]
            hi = order[min(len(order) - 1, idx + 1)]
            return lo, hi
        return level, level
