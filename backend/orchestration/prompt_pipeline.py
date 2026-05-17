from __future__ import annotations

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
    # NO internal queue — use AsyncioSessionTaskQueue as the entry point

    @classmethod
    def from_provider(
        cls,
        provider: str,
        page: object,
        registry: ProviderAdapterRegistry,
        extractor: Extractor,
    ) -> "PromptPipeline":
        return cls(adapter=registry.create(provider, page), extractor=extractor)

    async def run_once(self, prompt: str, original_text: str) -> dict[str, str]:
        """Process a single prompt through the pipeline.

        This method is designed to be called as a handler registered
        with AsyncioSessionTaskQueue.register_handler().
        """
        adapter_response = await self.adapter.send_prompt(SendPromptRequest(prompt=prompt))
        extracted_content = self.extractor.extract(adapter_response)
        patch_payload = self.patch_pipeline.generate(
            original_text=original_text,
            patched_text=extracted_content,
        )
        patch_payload["extracted_content"] = extracted_content
        return patch_payload
