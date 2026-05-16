from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class PatchPipelineRequest(BaseModel):
    original_text: str
    instruction: str


class PatchPipelineResult(BaseModel):
    patched_text: str
    diff: str | None = None


class BasePatchPipeline(ABC):
    @abstractmethod
    async def run(self, request: PatchPipelineRequest) -> PatchPipelineResult:
        raise NotImplementedError
