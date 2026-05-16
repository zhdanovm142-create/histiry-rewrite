from __future__ import annotations

from dataclasses import dataclass, field
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from backend.browser.playwright.cdp import CDPBrowserClient
from backend.browser.sessions import ChatSession, SessionState


SessionEventPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class SessionManager:
    """Registry of browser chat sessions backed by one user Chromium."""

    browser_client: CDPBrowserClient
    _sessions: Dict[str, ChatSession] = field(default_factory=dict)
    _reconnect_locks: Dict[str, asyncio.Lock] = field(default_factory=dict)
    event_publisher: SessionEventPublisher | None = None

    async def create_session(self, session_id: str) -> ChatSession:
        if session_id in self._sessions:
            raise ValueError(f"Session {session_id} already exists")

        session = ChatSession(session_id=session_id, browser_client=self.browser_client)
        await session.connect()
        self._sessions[session_id] = session
        return session

    async def delete_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        await session.disconnect()

    async def health_check(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.state != SessionState.CONNECTED:
            return False

        try:
            _ = session.page.url
            return not session.page.is_closed()
        except Exception:
            return False

    async def reconnect(self, session_id: str) -> ChatSession:
        lock = self._reconnect_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = ChatSession(session_id=session_id, browser_client=self.browser_client)
                self._sessions[session_id] = session

            try:
                await session.restart_context()
            except Exception as error:  # noqa: BLE001
                await self._publish_event(
                    "session_reconnect_failure",
                    {"session_id": session_id, "healthy": False, "error": str(error)},
                )
                raise

            await self._publish_event(
                "session_health",
                {"session_id": session_id, "healthy": True},
            )
            return session

    async def _publish_event(self, event_name: str, payload: dict[str, Any]) -> None:
        if self.event_publisher is None:
            return
        await self.event_publisher(event_name, payload)

    async def close(self) -> None:
        for session_id in list(self._sessions):
            await self.delete_session(session_id)
        await self.browser_client.disconnect()
