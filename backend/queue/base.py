from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from .events import EventBus
from .models import TaskEnvelope

TaskHandler = Callable[[TaskEnvelope], Awaitable[dict]]


class BaseTaskQueue(ABC):
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def enqueue(self, task: TaskEnvelope) -> None:
        ...

    @abstractmethod
    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        ...
