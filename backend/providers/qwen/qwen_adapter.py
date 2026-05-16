from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.providers.base.streaming_detector import BaseStreamingDetector, StreamingStatus


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


class QwenStreamingDetector(BaseStreamingDetector):
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


class QwenAdapter:
    def __init__(self, page: Any, selectors: QwenSelectors | None = None) -> None:
        self.page = page
        self.selectors = selectors or QwenSelectors()
        self.detector = QwenStreamingDetector(self.selectors)

    def locate_and_send_prompt(self, prompt: str) -> None:
        input_el = self.page.locator(self.selectors.prompt_input).first
        input_el.fill(prompt)
        self.page.locator(self.selectors.send_button).first.click()

    def check_streaming_complete(self) -> StreamingStatus:
        state = {
            "has_streaming_cursor": self.page.locator(self.selectors.streaming_cursor).count() > 0,
            "has_done_marker": self.page.locator(self.selectors.done_marker).count() > 0,
            "send_enabled": self.page.locator(self.selectors.send_button).first.is_enabled(),
            "has_assistant_message": self.page.locator(self.selectors.message_blocks).count() > 0,
            "has_root": self.page.locator(self.selectors.stale_dom_marker).count() > 0,
            "chat_id": self.page.url,
        }
        return self.detector.detect(state)

    def extract_response(self) -> dict[str, Any]:
        last = self.page.locator(self.selectors.message_blocks).last
        markdown = last.inner_text().strip()
        code_blocks = re.findall(r"```(?:[\w+-]+)?\n(.*?)```", markdown, flags=re.DOTALL)
        return {"markdown": markdown, "code_blocks": [b.strip() for b in code_blocks]}

    def detect_error(self) -> str | None:
        if self.page.locator(self.selectors.rate_limit_error).count() > 0:
            return "rate_limit"
        if self.page.locator(self.selectors.disconnect_error).count() > 0:
            return "disconnect"
        if self.detector.is_stale({
            "has_root": self.page.locator(self.selectors.stale_dom_marker).count() > 0,
            "chat_id": self.page.url,
        }):
            return "stale_dom"
        return None
