"""Package: project.backend.queue.

Re-exports queue contracts from ``backend.queue`` to keep import points explicit.
"""

from backend.queue import (
    AsyncioSessionTaskQueue,
    BaseTaskQueue,
    LegacyTaskQueueAdapter,
    LegacyTaskQueueContract,
    QueueConsumer,
    QueuePopResult,
    QueueStats,
    QueueTask,
    TaskEnvelope,
    TaskHandler,
    TaskPayload,
    TaskResult,
    TaskState,
    TaskType,
)

__all__ = [
    "AsyncioSessionTaskQueue",
    "BaseTaskQueue",
    "LegacyTaskQueueAdapter",
    "LegacyTaskQueueContract",
    "QueueConsumer",
    "QueuePopResult",
    "QueueStats",
    "QueueTask",
    "TaskEnvelope",
    "TaskHandler",
    "TaskPayload",
    "TaskResult",
    "TaskState",
    "TaskType",
]
