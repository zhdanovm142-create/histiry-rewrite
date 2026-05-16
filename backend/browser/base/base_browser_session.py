from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class NavigateRequest(BaseModel):
    url: str
    wait_until: str = "domcontentloaded"


class BrowserActionResult(BaseModel):
    ok: bool
    details: str | None = None


class BaseBrowserSession(ABC):
    """Only layer allowed to perform direct browser automation calls."""

    @abstractmethod
    async def start(self) -> BrowserActionResult:
        raise NotImplementedError

    @abstractmethod
    async def navigate(self, request: NavigateRequest) -> BrowserActionResult:
        raise NotImplementedError

    @abstractmethod
    async def screenshot(self, path: str) -> BrowserActionResult:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> BrowserActionResult:
        raise NotImplementedError
