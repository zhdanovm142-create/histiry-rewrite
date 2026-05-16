from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class StreamingStatus(BaseModel):
    generating: bool
    progress_hint: str | None = None


class BaseStreamingDetector(ABC):
    @abstractmethod
    async def check(self) -> StreamingStatus:
        raise NotImplementedError

    @abstractmethod
    async def wait_complete(self, timeout_ms: int = 120_000) -> StreamingStatus:
        raise NotImplementedError
