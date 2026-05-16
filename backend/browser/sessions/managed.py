from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from playwright.async_api import BrowserContext, Page

from backend.browser.playwright.cdp import CDPBrowserClient, CDPConnectError


class SessionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"


@dataclass(slots=True)
class ManagedBrowserSession:
    """Session that isolates work in a dedicated context and page."""

    session_id: str
    browser_client: CDPBrowserClient

    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None
    _state: SessionState = SessionState.DISCONNECTED

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError(f"Session {self.session_id} has no active context")
        return self._context

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError(f"Session {self.session_id} has no active page")
        return self._page

    @property
    def state(self) -> SessionState:
        return self._state

    async def connect(self) -> None:
        try:
            await self.browser_client.connect_over_cdp()
            self._context = await self.browser_client.browser.new_context()
            self._page = await self._context.new_page()
            self._state = SessionState.CONNECTED
        except CDPConnectError as error:
            raise RuntimeError(
                f"Session {self.session_id} failed to connect after {error.attempts} attempts"
            ) from error

    async def disconnect(self) -> None:
        if self._page is not None and not self._page.is_closed():
            await self._page.close()
        self._page = None

        if self._context is not None:
            await self._context.close()
        self._context = None

        self._state = SessionState.DISCONNECTED

    async def refresh(self) -> None:
        if self._state != SessionState.CONNECTED:
            raise RuntimeError("Session is not connected")
        await self.page.reload(wait_until="domcontentloaded")

    async def restart_context(self) -> None:
        await self.disconnect()
        try:
            await self.connect()
        except RuntimeError as error:
            raise RuntimeError(
                f"Session {self.session_id} failed to restart context: {error}"
            ) from error


class ChatSession(ManagedBrowserSession):
    """Specialized session wrapper for chat orchestration use cases."""

    async def ensure_ready(self) -> Page:
        if self.state != SessionState.CONNECTED:
            await self.connect()
        return self.page
