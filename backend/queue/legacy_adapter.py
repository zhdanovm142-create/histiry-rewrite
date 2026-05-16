from __future__ import annotations

import asyncio
from collections import deque

from .base import BaseTaskQueue
from .base_task_queue import LegacyTaskQueueContract, QueuePopResult, QueueStats, QueueTask
from .models import TaskEnvelope, TaskPayload, TaskType


class LegacyTaskQueueAdapter(LegacyTaskQueueContract):
    """Adapter from deprecated ``push/pop/ack/stats`` to canonical queue runtime APIs."""

    def __init__(self, queue: BaseTaskQueue, default_task_type: TaskType = TaskType.SEND_PROMPT) -> None:
        self._queue = queue
        self._default_task_type = default_task_type
        self._buffer: deque[QueueTask] = deque()
        self._in_flight: set[str] = set()
        self._pending = asyncio.Queue[QueueTask]()

    async def start(self) -> None:
        await self._queue.start()

    async def stop(self) -> None:
        await self._queue.stop()

    async def push(self, task: QueueTask) -> None:
        envelope = TaskEnvelope(
            payload=TaskPayload(
                session_id=task.payload.get("session_id", "legacy"),
                task_type=self._default_task_type,
                data=task.payload,
            )
        )
        await self._queue.enqueue(envelope)
        self._buffer.append(task)
        await self._pending.put(task)

    async def pop(self) -> QueuePopResult:
        task = await self._pending.get()
        self._in_flight.add(task.id)
        return QueuePopResult(task=task)

    async def ack(self, task_id: str) -> None:
        self._in_flight.discard(task_id)

    async def stats(self) -> QueueStats:
        return QueueStats(queued=self._pending.qsize(), in_flight=len(self._in_flight))
