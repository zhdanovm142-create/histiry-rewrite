from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class ScreenshotRequest(BaseModel):
    url: str
    output_path: str


class ScreenshotResult(BaseModel):
    path: str
    bytes_written: int


class BaseScreenshotService(ABC):
    @abstractmethod
    async def capture(self, request: ScreenshotRequest) -> ScreenshotResult:
        raise NotImplementedError
