from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Protocol

from pydantic import BaseModel, Field


class LocateInputRequest(BaseModel):
    selector: str | None = None
    timeout_ms: int = 30_000


class LocateInputResult(BaseModel):
    found: bool
    selector: str | None = None
    details: str | None = None


class SendPromptRequest(BaseModel):
    prompt: str
    metadata: dict[str, str] = Field(default_factory=dict)


class SendPromptResult(BaseModel):
    accepted: bool
    request_id: str | None = None


class StreamWaitRequest(BaseModel):
    request_id: str | None = None
    timeout_ms: int = 120_000


class StreamWaitResult(BaseModel):
    completed: bool
    elapsed_ms: int


class ExtractResponseResult(BaseModel):
    text: str
    request_id: str | None = None


class ExtractMarkdownResult(BaseModel):
    markdown: str


class GenerationState(BaseModel):
    generating: bool
    reason: str | None = None


class ProviderError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class DetectErrorsResult(BaseModel):
    errors: list[ProviderError]


class SupportsProviderMetadata(Protocol):
    provider_name: str


class BaseProviderAdapter(ABC):
    """Provider adapter contract for provider-specific UI/API automation."""

    @property
    @abstractmethod
    def selectors(self) -> Any:
        """Return the provider-specific selectors dataclass."""
        ...

    @property
    @abstractmethod
    def streaming_detector(self) -> Any:
        """Return the provider-specific streaming detector instance."""
        ...

    # --- Shared implementations (identical in both adapters) ---

    async def locate_and_send_prompt(self, prompt: str) -> None:
        input_el = self.page.locator(self.selectors.prompt_input).first
        await input_el.fill(prompt)
        await self.page.locator(self.selectors.send_button).first.click()

    async def check_streaming_complete(self) -> Any:
        """Build DOM state dict and delegate to streaming detector."""
        state = {
            "has_streaming_cursor": await self.page.locator(self.selectors.streaming_cursor).count() > 0,
            "has_done_marker": await self.page.locator(self.selectors.done_marker).count() > 0,
            "send_enabled": await self.page.locator(self.selectors.send_button).first.is_enabled(),
            "has_assistant_message": await self.page.locator(self.selectors.message_blocks).count() > 0,
            "has_root": await self.page.locator(self.selectors.stale_dom_marker).count() > 0,
            "chat_id": self.page.url,
        }
        return self.streaming_detector.detect(state)

    async def _extract_response_payload(self) -> dict[str, Any]:
        last = self.page.locator(self.selectors.message_blocks).last
        markdown = (await last.inner_text()).strip()
        code_blocks = re.findall(r"```(?:[\w+-]+)?\n(.*?)```", markdown, flags=re.DOTALL)
        return {"markdown": markdown, "code_blocks": [b.strip() for b in code_blocks]}

    async def detect_error(self) -> str | None:
        if await self.page.locator(self.selectors.rate_limit_error).count() > 0:
            return "rate_limit"
        if await self.page.locator(self.selectors.disconnect_error).count() > 0:
            return "disconnect"
        if self.streaming_detector.is_stale({
            "has_root": await self.page.locator(self.selectors.stale_dom_marker).count() > 0,
            "chat_id": self.page.url,
        }):
            return "stale_dom"
        return None

    # --- Base class already defines these as abstract — now implement them: ---

    async def send_prompt(self, request: SendPromptRequest) -> SendPromptResult:
        await self.locate_and_send_prompt(request.prompt)
        return SendPromptResult(accepted=True)

    async def wait_stream_complete(self, request: StreamWaitRequest) -> StreamWaitResult:
        status = await self.check_streaming_complete()
        return StreamWaitResult(completed=status.is_complete, elapsed_ms=0)

    async def extract_response(self) -> ExtractResponseResult:
        payload = await self._extract_response_payload()
        return ExtractResponseResult(text=payload["markdown"])

    async def extract_markdown(self) -> ExtractMarkdownResult:
        payload = await self._extract_response_payload()
        return ExtractMarkdownResult(markdown=payload["markdown"])

    async def is_generating(self) -> GenerationState:
        status = await self.check_streaming_complete()
        return GenerationState(generating=status.is_streaming, reason=status.reason)

    async def detect_errors(self) -> DetectErrorsResult:
        code = await self.detect_error()
        if not code:
            return DetectErrorsResult(errors=[])
        return DetectErrorsResult(
            errors=[
                ProviderError(
                    code=code,
                    message=f"Provider error: {code}",
                    retryable=code in {"rate_limit", "disconnect"},
                )
            ]
        )

    @abstractmethod
    async def locate_input(self, request: LocateInputRequest) -> LocateInputResult:
        raise NotImplementedError
