from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Playwright,
    async_playwright,
)


@dataclass(slots=True)
class RetryConfig:
    """Retry policy for CDP connection attempts."""

    attempts: int = 3
    base_delay_ms: int = 300
    max_delay_ms: int = 3_000
    jitter: float = 0.2


class CDPConnectError(RuntimeError):
    """Raised when connection to CDP endpoint fails."""

    def __init__(self, message: str, *, attempts: int, cause: Exception) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.cause = cause


@dataclass(slots=True)
class CDPConnectionConfig:
    """Configuration for connecting to user-managed Chromium over CDP."""

    cdp_url: str = "http://127.0.0.1:9222"
    context_index: int = 0
    retry: RetryConfig = field(default_factory=RetryConfig)


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

        last_error: Exception | None = None
        attempts = max(1, self._config.retry.attempts)

        for attempt in range(1, attempts + 1):
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(
                    self._config.cdp_url
                )
                return self._browser
            except Exception as error:  # noqa: BLE001
                last_error = error
                if not self._is_retryable_error(error) or attempt >= attempts:
                    break

                delay = self._compute_delay(attempt)
                await asyncio.sleep(delay)

        raise CDPConnectError(
            f"Failed to connect to CDP endpoint {self._config.cdp_url}",
            attempts=attempts,
            cause=last_error if last_error is not None else RuntimeError("unknown error"),
        ) from last_error

    def _is_retryable_error(self, error: Exception) -> bool:
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True

        if isinstance(error, PlaywrightError):
            text = str(error).lower()
            return any(
                token in text
                for token in ("timeout", "econnrefused", "connection", "closed")
            )

        return False

    def _compute_delay(self, attempt: int) -> float:
        retry = self._config.retry
        base_seconds = max(0, retry.base_delay_ms) / 1000
        max_seconds = max(base_seconds, retry.max_delay_ms / 1000)
        exp_delay = min(max_seconds, base_seconds * (2 ** (attempt - 1)))

        jitter = max(0.0, retry.jitter)
        if jitter == 0:
            return exp_delay

        spread = exp_delay * jitter
        return max(0.0, random.uniform(exp_delay - spread, exp_delay + spread))

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
