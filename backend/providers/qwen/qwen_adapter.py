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
class QwenSelectors:
    prompt_input: str = "textarea[data-testid='chat-input'], textarea"
    send_button: str = "button[data-testid='send-button'], button.send-btn"
    message_blocks: str = "div[data-role='assistant-message'], .assistant-message"
    streaming_cursor: str = ".typing-cursor, .streaming"
    done_marker: str = "[data-finished='true'], .message-complete"
    rate_limit_error: str = ".error-rate-limit, [data-error-code='429']"
    disconnect_error: str = ".error-network, .connection-lost"
    stale_dom_marker: str = "#app, [data-page='chat']"


class QwenStreamingDetector(StreamingDetector):
    def __init__(self, selectors: QwenSelectors | None = None) -> None:
        self.selectors = selectors or QwenSelectors()

    def detect(self, dom_state: dict[str, Any]) -> StreamingStatus:
        if dom_state.get("has_streaming_cursor"):
            return StreamingStatus(is_streaming=True, is_complete=False, reason="cursor")
        if dom_state.get("has_done_marker"):
            return StreamingStatus(is_streaming=False, is_complete=True, reason="done_marker")
        if dom_state.get("send_enabled") and dom_state.get("has_assistant_message"):
            return StreamingStatus(is_streaming=False, is_complete=True, reason="send_enabled")
        return StreamingStatus(is_streaming=False, is_complete=False, reason="unknown")

    def is_stale(self, dom_state: dict[str, Any]) -> bool:
        return not dom_state.get("has_root", True) or dom_state.get("chat_id") is None


class QwenAdapter(BaseProviderAdapter):
    def __init__(self, page: Any, selectors: QwenSelectors | None = None) -> None:
        self.page = page
        self._selectors = selectors or QwenSelectors()
        self._detector = QwenStreamingDetector(self._selectors)

    @property
    def selectors(self) -> QwenSelectors:
        return self._selectors

    @property
    def streaming_detector(self) -> StreamingDetector:
        return self._detector

    async def locate_input(self, request: LocateInputRequest) -> LocateInputResult:
        selector = request.selector or self.selectors.prompt_input
        found = await self.page.locator(selector).count() > 0
        return LocateInputResult(found=found, selector=selector if found else None)
