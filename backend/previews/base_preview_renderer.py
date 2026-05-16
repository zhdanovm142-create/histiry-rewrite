from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class PreviewRenderRequest(BaseModel):
    markdown: str


class PreviewRenderResult(BaseModel):
    html: str


class BasePreviewRenderer(ABC):
    @abstractmethod
    async def render(self, request: PreviewRenderRequest) -> PreviewRenderResult:
        raise NotImplementedError
