from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Protocol

from backend.patching import DiffPatchPipeline
from backend.providers.base.base_provider_adapter import SendPromptRequest, SendPromptResult
from backend.providers.registry import ProviderAdapterRegistry


class PromptAdapter(Protocol):
    async def send_prompt(self, request: SendPromptRequest) -> SendPromptResult: ...


class Extractor(Protocol):
    def extract(self, adapter_response: SendPromptResult) -> str: ...


@dataclass(slots=True)
class PromptPipeline:
    """User Input → Queue → Adapter.send_prompt → wait complete → extract → patch generate."""

    adapter: PromptAdapter
    extractor: Extractor
    patch_pipeline: DiffPatchPipeline = field(default_factory=DiffPatchPipeline)
    queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)

    @classmethod
    def from_provider(
        cls,
        provider: str,
        page: object,
        registry: ProviderAdapterRegistry,
        extractor: Extractor,
    ) -> "PromptPipeline":
        return cls(adapter=registry.create(provider, page), extractor=extractor)

    async def enqueue_user_input(self, user_input: str) -> None:
        await self.queue.put(user_input)

    async def run_once(self, original_text: str) -> dict[str, str]:
        prompt = await self.queue.get()
        try:
            adapter_response = await self.adapter.send_prompt(SendPromptRequest(prompt=prompt))
            extracted_content = self.extractor.extract(adapter_response)
            patch_payload = self.patch_pipeline.generate(
                original_text=original_text,
                patched_text=extracted_content,
            )
            patch_payload["extracted_content"] = extracted_content
            return patch_payload
        finally:
            self.queue.task_done()
