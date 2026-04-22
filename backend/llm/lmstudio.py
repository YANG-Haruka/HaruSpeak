"""LM Studio local LLM backend.

Speaks OpenAI's chat/completions shape but tuned for local reasoning-heavy
models (Qwen3, DeepSeek-R1, and similar).

Differences from the cloud backend:
  * max_tokens is floored at 8192. Local inference has no per-token cost,
    and reasoning-tuned models routinely burn 1000+ tokens on chain-of-
    thought before producing any visible content. Respecting a caller's
    `max_tokens=200` hint here means the user never sees a reply.
  * /no_think + anti-reasoning directive appended to every system prompt.
  * reasoning_content fallback — some Qwen3 variants stream the answer
    on the reasoning channel rather than content.
  * <think>…</think> tag stripping in both complete() and stream().
  * Prose-style thinking preamble stripping ("Thinking Process:" etc.)
    via a buffered state machine in the stream path.
  * "Heavy reasoning" warning when >80% of completion_tokens were
    chain-of-thought — a signal to swap models.
  * Only `json_schema` response_format is supported (LM Studio rejects
    `json_object`).
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

from ._thinking import strip_thinking

log = logging.getLogger(__name__)


_MAX_TOKENS_FLOOR = 8192

_SYSTEM_SUFFIX = (
    "/no_think\n"
    "Do NOT output any thinking, reasoning, analysis, chain-of-thought, "
    "<think> tags, or explanations. Respond with ONLY the final answer."
)


class LMStudioLLM:
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "",
        temperature: float = 1.0,
        api_key: str = "lm-studio",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def _system(self, system: str) -> str:
        return f"{system}\n\n{_SYSTEM_SUFFIX}"

    def _max_tokens(self, hint: int) -> int:
        return max(hint, _MAX_TOKENS_FLOOR)

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> str:
        client = self._get_client()
        eff = self._max_tokens(max_tokens)
        log.info(
            "[llm:lmstudio] complete  model=%r  msgs=%d  max=%d(hint=%d)  format=%s",
            self._model, len(messages), eff, max_tokens,
            response_format.get("type") if response_format else "text",
        )
        kwargs: dict = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": eff,
            "messages": [{"role": "system", "content": self._system(system)}, *messages],
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        try:
            resp = await client.chat.completions.create(**kwargs)
        except Exception as e:
            log.error("[llm:lmstudio] complete FAILED  model=%r  err=%s", self._model, e)
            raise
        choice = resp.choices[0]
        msg = choice.message
        text = msg.content or ""
        reasoning = getattr(msg, "reasoning_content", None)
        if not text and reasoning:
            text = reasoning
        text = strip_thinking(text)
        finish = getattr(choice, "finish_reason", None)
        usage = getattr(resp, "usage", None)
        if not text:
            attrs = {k: v for k, v in (msg.model_dump() if hasattr(msg, "model_dump") else {}).items() if v}
            log.warning(
                "[llm:lmstudio] complete returned EMPTY content  model=%r  finish=%s  usage=%s  message_fields=%s",
                self._model, finish, usage, attrs,
            )
        else:
            log.info("[llm:lmstudio] complete ok  chars=%d  finish=%s  usage=%s  had_reasoning=%s",
                     len(text), finish, usage, bool(reasoning))
            if usage is not None:
                rt = getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None) or 0
                total = getattr(usage, "completion_tokens", 0) or 0
                if total and rt and rt / total > 0.8:
                    log.warning(
                        "[llm:lmstudio] heavy reasoning: %d/%d tokens (%.0f%%) in chain-of-thought. "
                        "Consider disabling thinking in LM Studio or switching to a non-reasoning model.",
                        rt, total, 100 * rt / total,
                    )
        return text

    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 512,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        eff = self._max_tokens(max_tokens)
        log.info("[llm:lmstudio] stream  model=%r  msgs=%d  max=%d(hint=%d)",
                 self._model, len(messages), eff, max_tokens)
        try:
            stream = await client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                max_tokens=eff,
                messages=[{"role": "system", "content": self._system(system)}, *messages],
                stream=True,
            )
        except Exception as e:
            log.error("[llm:lmstudio] stream FAILED  model=%r  err=%s", self._model, e)
            raise

        # State machine:
        #   in_think_tag  — inside <think>…</think>, drop everything
        #   preamble_buf  — first 300 chars held back so we can detect
        #                   prose-style "Thinking Process:" preambles and
        #                   strip them before the user sees any of it
        chunk_count = 0
        reasoning_chars = 0
        last_finish = None
        first_nonempty_sample: str | None = None
        in_think_tag = False
        preamble_buf = ""
        preamble_released = False
        PREAMBLE_MAX = 300

        def _filter(c: str) -> list[str]:
            nonlocal in_think_tag
            out: list[str] = []
            i = 0
            while i < len(c):
                if in_think_tag:
                    end = c.find("</think>", i)
                    if end == -1:
                        return out
                    in_think_tag = False
                    i = end + len("</think>")
                else:
                    start = c.find("<think>", i)
                    if start == -1:
                        out.append(c[i:])
                        return out
                    if start > i:
                        out.append(c[i:start])
                    in_think_tag = True
                    i = start + len("<think>")
            return out

        async for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta
            if getattr(choice, "finish_reason", None):
                last_finish = choice.finish_reason
            if not delta:
                continue
            reasoning = getattr(delta, "reasoning_content", None)
            content = getattr(delta, "content", None)
            if reasoning:
                reasoning_chars += len(reasoning)
                if first_nonempty_sample is None:
                    first_nonempty_sample = f"reasoning_content={reasoning[:60]!r}"
            if not content:
                continue
            if first_nonempty_sample is None:
                first_nonempty_sample = f"content={content[:60]!r}"
            for seg in _filter(content):
                if not seg:
                    continue
                if preamble_released:
                    chunk_count += 1
                    yield seg
                    continue
                preamble_buf += seg
                if len(preamble_buf) < PREAMBLE_MAX:
                    continue
                cleaned = strip_thinking(preamble_buf)
                preamble_released = True
                if cleaned:
                    chunk_count += 1
                    yield cleaned

        if not preamble_released and preamble_buf:
            cleaned = strip_thinking(preamble_buf)
            if cleaned:
                chunk_count += 1
                yield cleaned

        if chunk_count == 0:
            log.warning(
                "[llm:lmstudio] stream returned ZERO content chunks  model=%r  finish=%s  "
                "reasoning_chars=%d  first_nonempty=%s",
                self._model, last_finish, reasoning_chars, first_nonempty_sample,
            )
        else:
            log.info(
                "[llm:lmstudio] stream ok  chunks=%d  reasoning_chars=%d  finish=%s",
                chunk_count, reasoning_chars, last_finish,
            )
