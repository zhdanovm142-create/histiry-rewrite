from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Protocol

from backend.patching import DiffPatchPipeline


class PromptAdapter(Protocol):
    async def send_prompt(self, prompt: str) -> str: ...


class Extractor(Protocol):
    def extract(self, adapter_response: str) -> str: ...


@dataclass(slots=True)
class PromptPipeline:
    """User Input → Queue → Adapter.send_prompt → wait complete → extract → patch generate."""

    adapter: PromptAdapter
    extractor: Extractor
    patch_pipeline: DiffPatchPipeline = field(default_factory=DiffPatchPipeline)
    queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)

    async def enqueue_user_input(self, user_input: str) -> None:
        await self.queue.put(user_input)

    async def run_once(self, original_text: str) -> dict[str, str]:
        prompt = await self.queue.get()
        try:
            adapter_response = await self.adapter.send_prompt(prompt)
            extracted_content = self.extractor.extract(adapter_response)
            patch_payload = self.patch_pipeline.generate(
                original_text=original_text,
                patched_text=extracted_content,
            )
            patch_payload["extracted_content"] = extracted_content
            return patch_payload
        finally:
            self.queue.task_done()
