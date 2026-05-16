from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable

from .models import TaskResult

TaskEventHandler = Callable[[TaskResult], Awaitable[None]]


class EventBus:
    """Simple async event bus for task state events."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[TaskEventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: TaskEventHandler) -> None:
        self._handlers[event_name].append(handler)

    async def publish(self, event_name: str, event: TaskResult) -> None:
        handlers = tuple(self._handlers.get(event_name, ()))
        if not handlers:
            return
        await asyncio.gather(*(handler(event) for handler in handlers))
