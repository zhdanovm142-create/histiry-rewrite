from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.providers.base.base_provider_adapter import (
    BaseProviderAdapter,
    LocateInputRequest,
    LocateInputResult,
)
from backend.providers.base.streaming_detector import StreamingDetector, StreamingStatus


@dataclass(frozen=True)
class DeepSeekSelectors:
    prompt_input: str = "textarea#chat-input, textarea[placeholder*='Send']"
    send_button: str = "button#send, button[data-testid='send']"
    message_blocks: str = ".assistant .message-content, [data-role='assistant']"
    streaming_cursor: str = ".ds-typing, .blinking-caret"
    done_marker: str = ".message-end, [data-stream='done']"
    rate_limit_error: str = ".rate-limit-warning, [data-code='429']"
    disconnect_error: str = ".ws-disconnected, .network-error"
    stale_dom_marker: str = "main.chat-layout, #root"


class DeepSeekStreamingDetector(StreamingDetector):
    def __init__(self, selectors: DeepSeekSelectors | None = None) -> None:
        self.selectors = selectors or DeepSeekSelectors()

    def detect(self, dom_state: dict[str, Any]) -> StreamingStatus:
        if dom_state.get("has_streaming_cursor") and not dom_state.get("has_done_marker"):
            return StreamingStatus(is_streaming=True, is_complete=False, reason="cursor_active")
        if dom_state.get("has_done_marker"):
            return StreamingStatus(is_streaming=False, is_complete=True, reason="done_marker")
        if dom_state.get("send_enabled") and dom_state.get("assistant_len", 0) > 0:
            return StreamingStatus(is_streaming=False, is_complete=True, reason="idle_after_output")
        return StreamingStatus(is_streaming=False, is_complete=False, reason="pending")

    def is_stale(self, dom_state: dict[str, Any]) -> bool:
        return not dom_state.get("has_root", True) or dom_state.get("conversation_id") is None


class DeepSeekAdapter(BaseProviderAdapter):
    def __init__(self, page: Any, selectors: DeepSeekSelectors | None = None) -> None:
        self.page = page
        self._selectors = selectors or DeepSeekSelectors()
        self._detector = DeepSeekStreamingDetector(self._selectors)

    @property
    def selectors(self) -> DeepSeekSelectors:
        return self._selectors

    @property
    def streaming_detector(self) -> StreamingDetector:
        return self._detector

    async def locate_input(self, request: LocateInputRequest) -> LocateInputResult:
        selector = request.selector or self.selectors.prompt_input
        found = await self.page.locator(selector).count() > 0
        return LocateInputResult(found=found, selector=selector if found else None)
