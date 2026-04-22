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


class OpenAICloudLLM:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 1.0,
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
        kwargs: dict = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
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
