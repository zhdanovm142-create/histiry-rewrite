from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StreamingStatus:
    """Provider-level streaming status snapshot."""

    is_streaming: bool
    is_complete: bool
    reason: str | None = None


class StreamingDetector(ABC):
    """Provider-specific streaming detector interface.

    This base class is intentionally DOM-agnostic. Every provider implementation
    must rely only on selectors/state available in its own package.
    """

    @abstractmethod
    def detect(self, dom_state: Any) -> StreamingStatus:
        """Return whether streaming is still active and whether completion is reached."""
        raise NotImplementedError

    @abstractmethod
    def is_stale(self, dom_state: Any) -> bool:
        """Return True when provider page/session is stale and requires reload."""
        raise NotImplementedError


# Backwards-compatible alias
BaseStreamingDetector = StreamingDetector
