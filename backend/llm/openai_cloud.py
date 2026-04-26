"""OpenAI cloud / OpenAI-compatible proxy LLM.

Targets production hosted endpoints — api.openai.com, jeniya.top,
openrouter, any gateway speaking the OpenAI chat/completions shape.

Contract with the rest of the app:
  * Caller `max_tokens` hints are respected as-is (for cost control —
    cloud tokens aren't free).
  * System prompt is passed through unmodified. Cloud models follow
    instructions without needing anti-reasoning directives.
  * No chain-of-thought stripping — cloud models emit clean `content`.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

log = logging.getLogger(__name__)


def _describe_json_schema(schema: dict) -> str:
    """Render a JSON schema as a one-line example-style hint for prompts.

    Only handles the schema flavours HaruSpeak actually uses (top-level
    object with simple properties, plus the suggestions case where one
    property is an array of objects). We don't try to be a general
    schema-to-prose engine.
    """
    if schema.get("type") != "object":
        return f"Reply with ONLY JSON matching: {schema}"

    def _example(p: dict) -> str:
        t = p.get("type")
        if t == "string":
            return '"<text>"'
        if t == "number" or t == "integer":
            return "0"
        if t == "boolean":
            return "true"
        if t == "array":
            inner = p.get("items") or {}
            return f"[{_example(inner)}]"
        if t == "object":
            inner_props = p.get("properties") or {}
            parts = [f'"{k}": {_example(v)}' for k, v in inner_props.items()]
            return "{" + ", ".join(parts) + "}"
        return "null"

    props = schema.get("properties") or {}
    body = ", ".join(f'"{k}": {_example(v)}' for k, v in props.items())
    return f"Reply with ONLY a JSON object in this exact shape: {{{body}}}"


class OpenAICloudLLM:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 1.0,
        thinking_mode: str = "disabled",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._temperature = temperature
        # "disabled" | "enabled" — DeepSeek v4 / OpenAI o1+ / Anthropic
        # extended-thinking models burn the entire token budget on internal
        # reasoning when this is on, leaving the visible `content` empty
        # for our small max_tokens calls (translations, suggestions). Off
        # by default; vendors that don't recognise the field ignore it.
        self._thinking_mode = thinking_mode
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def _is_deepseek(self) -> bool:
        return "deepseek" in self._base_url.lower()

    def _extra_body(self) -> dict:
        """Vendor-specific kwargs that the OpenAI SDK passes through verbatim
        as `extra_body`. We *only* emit the thinking toggle for DeepSeek —
        their v4 reasoning models default-on this and burn the token budget,
        but third-party proxies like jeniya.top reject unknown parameters
        with HTTP 429 even though real OpenAI silently ignores them."""
        if self._is_deepseek():
            return {"thinking": {"type": self._thinking_mode}}
        return {}

    def _normalize_response_format(self, fmt: dict | None) -> dict | None:
        """Vendor compatibility for `response_format`:
          * OpenAI accepts both json_object and json_schema.
          * DeepSeek (as of v4) accepts ONLY {"type": "json_object"} —
            {"type": "json_schema", ...} returns 400. We downgrade.
        Schema enforcement is then up to the model + system prompt."""
        if fmt is None:
            return None
        if self._is_deepseek() and fmt.get("type") == "json_schema":
            return {"type": "json_object"}
        return fmt

    def _schema_hint(self, fmt: dict | None) -> str | None:
        """When we downgrade json_schema → json_object for DeepSeek, the model
        loses the server-side shape contract. We compensate by generating a
        prompt suffix that describes the expected JSON keys.

        Returns None if no hint is needed (non-downgrade case)."""
        if fmt is None or not self._is_deepseek():
            return None
        if fmt.get("type") != "json_schema":
            return None
        schema = (fmt.get("json_schema") or {}).get("schema") or {}
        return _describe_json_schema(schema)

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> str:
        client = self._get_client()
        log.info(
            "[llm:cloud] complete  model=%r  msgs=%d  max=%d  format=%s",
            self._model, len(messages), max_tokens,
            response_format.get("type") if response_format else "text",
        )
        # If we're about to downgrade json_schema → json_object, append a
        # one-line shape hint to the system prompt. Without this DeepSeek
        # returns "valid JSON" but with arbitrary keys (e.g. "translation"
        # instead of our schema's "t"), and downstream parsers miss it.
        hint = self._schema_hint(response_format)
        effective_system = f"{system}\n\n{hint}" if hint else system
        kwargs: dict = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": effective_system}, *messages],
            "extra_body": self._extra_body(),
        }
        normalized = self._normalize_response_format(response_format)
        if normalized is not None:
            kwargs["response_format"] = normalized
        try:
            resp = await client.chat.completions.create(**kwargs)
        except Exception as e:
            log.error("[llm:cloud] complete FAILED  model=%r  base=%s  err=%s",
                      self._model, self._base_url, e)
            raise
        choice = resp.choices[0]
        text = choice.message.content or ""
        finish = getattr(choice, "finish_reason", None)
        usage = getattr(resp, "usage", None)
        log.info("[llm:cloud] complete ok  chars=%d  finish=%s  usage=%s",
                 len(text), finish, usage)
        return text

    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 512,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        log.info("[llm:cloud] stream  model=%r  msgs=%d  max=%d",
                 self._model, len(messages), max_tokens)
        try:
            stream = await client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, *messages],
                stream=True,
                extra_body=self._extra_body(),
            )
        except Exception as e:
            log.error("[llm:cloud] stream FAILED  model=%r  base=%s  err=%s",
                      self._model, self._base_url, e)
            raise
        chunks = 0
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                chunks += 1
                yield delta.content
        log.info("[llm:cloud] stream ok  chunks=%d", chunks)
