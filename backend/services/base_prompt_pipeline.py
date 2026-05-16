from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class PromptPipelineRequest(BaseModel):
    provider: str
    prompt: str
    trace_id: str | None = None


class PromptPipelineResult(BaseModel):
    response_text: str
    response_markdown: str | None = None


class BasePromptPipeline(ABC):
    @abstractmethod
    async def run(self, request: PromptPipelineRequest) -> PromptPipelineResult:
        raise NotImplementedError
