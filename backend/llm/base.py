from __future__ import annotations

from typing import AsyncIterator, Protocol


class LLMBackend(Protocol):
    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> str: ...

    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 512,
    ) -> AsyncIterator[str]: ...
