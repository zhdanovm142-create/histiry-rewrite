from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright


@dataclass(slots=True)
class CDPConnectionConfig:
    """Configuration for connecting to user-managed Chromium over CDP."""

    cdp_url: str = "http://127.0.0.1:9222"
    context_index: int = 0


class CDPBrowserClient:
    """Connects to an already running user Chromium via CDP.

    This client never launches a browser and therefore does not manage
    credentials, profiles, or tokens itself.
    """

    def __init__(self, config: CDPConnectionConfig | None = None) -> None:
        self._config = config or CDPConnectionConfig()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise RuntimeError("Browser is not connected.")
        return self._browser

    async def connect_over_cdp(self) -> Browser:
        """Connect to a user Chromium instance via the CDP endpoint."""
        if self._browser is not None and self._browser.is_connected():
            return self._browser

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.connect_over_cdp(
            self._config.cdp_url
        )
        return self._browser

    async def get_default_context(self) -> BrowserContext:
        """Return one of existing contexts from connected user browser."""
        browser = await self.connect_over_cdp()
        contexts = browser.contexts
        if not contexts:
            return await browser.new_context()

        idx = max(0, min(self._config.context_index, len(contexts) - 1))
        return contexts[idx]

    async def disconnect(self) -> None:
        """Close CDP connection without killing user browser process."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
