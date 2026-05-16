from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.browser.playwright.cdp import CDPBrowserClient
from backend.browser.sessions import ChatSession, SessionState
from backend.global_state import BROWSER_SESSION_REGISTRY


@dataclass
class SessionManager:
    """Registry of browser chat sessions backed by one user Chromium."""

    browser_client: CDPBrowserClient
    session_registry: Any = BROWSER_SESSION_REGISTRY

    async def create_session(self, session_id: str) -> ChatSession:
        if self.session_registry.get(session_id) is not None:
            raise ValueError(f"Session {session_id} already exists")

        session = ChatSession(session_id=session_id, browser_client=self.browser_client)
        await session.connect()
        self.session_registry.attach(session_id, session)
        return session

    async def delete_session(self, session_id: str) -> None:
        session = self.session_registry.detach(session_id)
        if session is None:
            return
        await session.disconnect()

    async def health_check(self, session_id: str) -> bool:
        session = self.session_registry.get(session_id)
        if session is None or session.state != SessionState.CONNECTED:
            return False

        try:
            _ = session.page.url
            return not session.page.is_closed()
        except Exception:
            return False

    async def reconnect(self, session_id: str) -> ChatSession:
        session = self.session_registry.get(session_id)
        if session is None:
            session = ChatSession(session_id=session_id, browser_client=self.browser_client)
            self.session_registry.attach(session_id, session)

        await session.restart_context()
        return session

    async def close(self) -> None:
        for session_id in self.session_registry.session_ids():
            await self.delete_session(session_id)
        await self.browser_client.disconnect()
