from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.providers.base.streaming_detector import BaseStreamingDetector, StreamingStatus


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


class DeepSeekStreamingDetector(BaseStreamingDetector):
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


class DeepSeekAdapter:
    def __init__(self, page: Any, selectors: DeepSeekSelectors | None = None) -> None:
        self.page = page
        self.selectors = selectors or DeepSeekSelectors()
        self.detector = DeepSeekStreamingDetector(self.selectors)

    def locate_and_send_prompt(self, prompt: str) -> None:
        prompt_box = self.page.locator(self.selectors.prompt_input).first
        prompt_box.click()
        prompt_box.fill(prompt)
        self.page.locator(self.selectors.send_button).first.click()

    def check_streaming_complete(self) -> StreamingStatus:
        assistant_messages = self.page.locator(self.selectors.message_blocks)
        state = {
            "has_streaming_cursor": self.page.locator(self.selectors.streaming_cursor).count() > 0,
            "has_done_marker": self.page.locator(self.selectors.done_marker).count() > 0,
            "send_enabled": self.page.locator(self.selectors.send_button).first.is_enabled(),
            "assistant_len": assistant_messages.count(),
            "has_root": self.page.locator(self.selectors.stale_dom_marker).count() > 0,
            "conversation_id": self.page.url,
        }
        return self.detector.detect(state)

    def extract_response(self) -> dict[str, Any]:
        text = self.page.locator(self.selectors.message_blocks).last.inner_text().strip()
        code_blocks = re.findall(r"```(?:[\w+-]+)?\n(.*?)```", text, flags=re.DOTALL)
        return {
            "markdown": text,
            "code_blocks": [block.strip() for block in code_blocks],
        }

    def detect_error(self) -> str | None:
        if self.page.locator(self.selectors.rate_limit_error).count() > 0:
            return "rate_limit"
        if self.page.locator(self.selectors.disconnect_error).count() > 0:
            return "disconnect"

        stale_state = {
            "has_root": self.page.locator(self.selectors.stale_dom_marker).count() > 0,
            "conversation_id": self.page.url,
        }
        if self.detector.is_stale(stale_state):
            return "stale_dom"

        return None
