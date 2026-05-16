from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel, Field


class QueueTask(BaseModel):
    id: str
    payload: dict[str, str] = Field(default_factory=dict)


class QueuePopResult(BaseModel):
    task: QueueTask | None = None


class QueueStats(BaseModel):
    queued: int
    in_flight: int


class QueueConsumer(Protocol):
    async def __call__(self, task: QueueTask) -> None: ...


class LegacyTaskQueueContract(ABC):
    """Deprecated legacy queue contract.

    Prefer the canonical runtime contract from ``backend.queue.base.BaseTaskQueue``
    (``start/stop/enqueue/register_handler``) for all new integrations.
    """

    @abstractmethod
    async def push(self, task: QueueTask) -> None:
        raise NotImplementedError

    @abstractmethod
    async def pop(self) -> QueuePopResult:
        raise NotImplementedError

    @abstractmethod
    async def ack(self, task_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stats(self) -> QueueStats:
        raise NotImplementedError
