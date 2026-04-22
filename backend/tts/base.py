from typing import Protocol


class TTSBackend(Protocol):
    async def synthesize(self, text: str, **kwargs) -> bytes: ...
