from __future__ import annotations

import asyncio
from collections.abc import Mapping

from .base import BaseTaskQueue, TaskHandler
from .events import EventBus
from .models import TaskEnvelope, TaskResult, TaskState


class AsyncioSessionTaskQueue(BaseTaskQueue):
    """Per-session queue with isolated worker coroutine per session."""

    def __init__(self, event_bus: EventBus, retry_delay_seconds: float = 1.0) -> None:
        super().__init__(event_bus=event_bus)
        self._retry_delay_seconds = retry_delay_seconds
        self._handlers: dict[str, TaskHandler] = {}
        self._session_queues: dict[str, asyncio.Queue[TaskEnvelope]] = {}
        self._workers: dict[str, asyncio.Task[None]] = {}
        self._shutdown = False

    async def start(self) -> None:
        self._shutdown = False

    async def stop(self) -> None:
        self._shutdown = True
        for worker in self._workers.values():
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers.values(), return_exceptions=True)
        self._workers.clear()
        self._session_queues.clear()

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        self._handlers[task_type] = handler

    async def enqueue(self, task: TaskEnvelope) -> None:
        session_id = task.payload.session_id
        queue = self._session_queues.get(session_id)
        if queue is None:
            queue = asyncio.Queue()
            self._session_queues[session_id] = queue
            self._workers[session_id] = asyncio.create_task(self._worker(session_id, queue))

        await queue.put(task)
        await self.event_bus.publish("task_state", self._result(task, TaskState.QUEUED))

    async def _worker(self, session_id: str, queue: asyncio.Queue[TaskEnvelope]) -> None:
        while not self._shutdown:
            task = await queue.get()
            try:
                await self._run_task(task)
            finally:
                queue.task_done()

    async def _run_task(self, task: TaskEnvelope) -> None:
        task_type = task.payload.task_type.value
        handler = self._handlers.get(task_type)

        if handler is None:
            await self.event_bus.publish(
                "task_state",
                self._result(task, TaskState.FAILED, error=f"Handler not found for {task_type}"),
            )
            return

        await self.event_bus.publish("task_state", self._result(task, TaskState.RUNNING))

        try:
            output = await handler(task)
        except Exception as exc:  # noqa: BLE001
            can_retry = task.attempt + 1 < task.max_attempts
            if can_retry:
                retry_task = TaskEnvelope(
                    id=task.id,
                    payload=task.payload,
                    created_at=task.created_at,
                    attempt=task.attempt + 1,
                    max_attempts=task.max_attempts,
                )
                await self.event_bus.publish(
                    "task_state",
                    self._result(task, TaskState.RETRY_SCHEDULED, error=str(exc)),
                )
                await asyncio.sleep(self._retry_delay_seconds)
                await self.enqueue(retry_task)
                return

            await self.event_bus.publish(
                "task_state",
                self._result(task, TaskState.FAILED, error=str(exc)),
            )
            return

        await self.event_bus.publish(
            "task_state",
            self._result(task, TaskState.SUCCEEDED, output=output),
        )

    def _result(
        self,
        task: TaskEnvelope,
        state: TaskState,
        output: Mapping[str, object] | None = None,
        error: str | None = None,
    ) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            session_id=task.payload.session_id,
            task_type=task.payload.task_type,
            state=state,
            output=output or {},
            error=error,
            attempt=task.attempt,
        )
