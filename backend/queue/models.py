from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


class TaskType(str, Enum):
    SEND_PROMPT = "send_prompt"
    REFRESH_PREVIEW = "refresh_preview"
    EXTRACT_RESPONSE = "extract_response"
    PREPARE_PATCH = "prepare_patch"


class TaskState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"


_ALLOWED_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.QUEUED: {TaskState.RUNNING, TaskState.FAILED},
    TaskState.RUNNING: {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.RETRY_SCHEDULED},
    TaskState.RETRY_SCHEDULED: {TaskState.QUEUED},
    TaskState.FAILED: set(),          # terminal
    TaskState.SUCCEEDED: set(),       # terminal
}


def validate_transition(current: TaskState, target: TaskState) -> None:
    """Raise ValueError if transition from current to target is not allowed."""
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"Invalid task state transition: {current.value} -> {target.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )


@dataclass(frozen=True)
class TaskPayload:
    session_id: str
    task_type: TaskType
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskEnvelope:
    payload: TaskPayload
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempt: int = 0
    max_attempts: int = 1


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    session_id: str
    task_type: TaskType
    state: TaskState
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    attempt: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
