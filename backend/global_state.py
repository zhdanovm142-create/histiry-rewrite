from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from backend.queue.events import EventBus
from backend.queue.models import TaskEnvelope
from backend.queue.session_queue import AsyncioSessionTaskQueue


class GlobalStateContract(ABC):
    """Unified contract for global registries/state stores."""

    @abstractmethod
    async def enqueue(self, task: TaskEnvelope) -> None: ...

    @abstractmethod
    async def dequeue(self, session_id: str) -> TaskEnvelope | None: ...

    @abstractmethod
    def register_adapter(self, provider_name: str, adapter: Any) -> None: ...

    @abstractmethod
    def unregister_adapter(self, provider_name: str) -> None: ...

    @abstractmethod
    def snapshot_state(self) -> dict[str, Any]: ...

    @abstractmethod
    def restore_state(self, state: Mapping[str, Any]) -> None: ...

    @abstractmethod
    def validate_state(self, state: Mapping[str, Any]) -> bool: ...

    @abstractmethod
    def health_report(self) -> dict[str, Any]: ...


@dataclass
class TaskQueueRegistry:
    """Serializable mirror of queue state + bootstrap helpers."""

    event_bus: EventBus = field(default_factory=EventBus)
    queue: AsyncioSessionTaskQueue = field(init=False)
    _pending: dict[str, list[TaskEnvelope]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.queue = AsyncioSessionTaskQueue(event_bus=self.event_bus)

    async def enqueue(self, task: TaskEnvelope) -> None:
        self._pending.setdefault(task.payload.session_id, []).append(task)
        await self.queue.enqueue(task)

    async def dequeue(self, session_id: str) -> TaskEnvelope | None:
        pending = self._pending.get(session_id)
        if not pending:
            return None
        return pending.pop(0)

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "pending": {
                session_id: [task.model_dump(mode="json") for task in tasks]
                for session_id, tasks in self._pending.items()
            }
        }

    def restore_state(self, state: Mapping[str, Any]) -> None:
        if not self.validate_state(state):
            raise ValueError("Invalid queue state")

        restored: dict[str, list[TaskEnvelope]] = {}
        for session_id, tasks in state["pending"].items():
            restored[session_id] = [TaskEnvelope.model_validate(task_data) for task_data in tasks]
        self._pending = restored

    def validate_state(self, state: Mapping[str, Any]) -> bool:
        pending = state.get("pending")
        if not isinstance(pending, Mapping):
            return False
        for session_id, tasks in pending.items():
            if not isinstance(session_id, str) or not isinstance(tasks, list):
                return False
        return True

    def health_report(self) -> dict[str, Any]:
        return {
            "sessions_with_pending": len(self._pending),
            "pending_tasks_total": sum(len(tasks) for tasks in self._pending.values()),
        }


@dataclass
class ProviderAdapterRegistry:
    _adapters: dict[str, Any] = field(default_factory=dict)

    def register_adapter(self, provider_name: str, adapter: Any) -> None:
        self._adapters[provider_name] = adapter

    def unregister_adapter(self, provider_name: str) -> None:
        self._adapters.pop(provider_name, None)

    def snapshot_state(self) -> dict[str, Any]:
        return {"providers": sorted(self._adapters.keys())}

    def restore_state(self, state: Mapping[str, Any]) -> None:
        if not self.validate_state(state):
            raise ValueError("Invalid adapter state")
        allowed = set(state["providers"])
        self._adapters = {name: adapter for name, adapter in self._adapters.items() if name in allowed}

    def validate_state(self, state: Mapping[str, Any]) -> bool:
        providers = state.get("providers")
        return isinstance(providers, list) and all(isinstance(p, str) for p in providers)

    def health_report(self) -> dict[str, Any]:
        return {"registered_providers": sorted(self._adapters.keys())}


@dataclass
class ConfigTimeoutRegistry:
    _timeouts_ms: dict[str, int] = field(default_factory=dict)
    _config: dict[str, Any] = field(default_factory=dict)

    def set_timeout(self, key: str, timeout_ms: int) -> None:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        self._timeouts_ms[key] = timeout_ms

    def snapshot_state(self) -> dict[str, Any]:
        return {"timeouts_ms": deepcopy(self._timeouts_ms), "config": deepcopy(self._config)}

    def restore_state(self, state: Mapping[str, Any]) -> None:
        if not self.validate_state(state):
            raise ValueError("Invalid config state")
        self._timeouts_ms = dict(state["timeouts_ms"])
        self._config = dict(state["config"])

    def validate_state(self, state: Mapping[str, Any]) -> bool:
        timeouts = state.get("timeouts_ms")
        config = state.get("config")
        if not isinstance(timeouts, Mapping) or not isinstance(config, Mapping):
            return False
        return all(isinstance(k, str) and isinstance(v, int) and v > 0 for k, v in timeouts.items())

    def health_report(self) -> dict[str, Any]:
        return {"timeouts": deepcopy(self._timeouts_ms), "config_keys": sorted(self._config.keys())}


@dataclass
class BrowserSessionRegistry:
    _sessions: dict[str, Any] = field(default_factory=dict)

    def attach(self, session_id: str, session: Any) -> None:
        self._sessions[session_id] = session

    def detach(self, session_id: str) -> Any | None:
        return self._sessions.pop(session_id, None)

    def get(self, session_id: str) -> Any | None:
        return self._sessions.get(session_id)

    def session_ids(self) -> list[str]:
        return list(self._sessions.keys())

    def snapshot_state(self) -> dict[str, Any]:
        return {"session_ids": sorted(self._sessions.keys())}

    def restore_state(self, state: Mapping[str, Any]) -> None:
        if not self.validate_state(state):
            raise ValueError("Invalid browser session state")
        allowed = set(state["session_ids"])
        self._sessions = {sid: session for sid, session in self._sessions.items() if sid in allowed}

    def validate_state(self, state: Mapping[str, Any]) -> bool:
        session_ids = state.get("session_ids")
        return isinstance(session_ids, list) and all(isinstance(sid, str) for sid in session_ids)

    def health_report(self) -> dict[str, Any]:
        return {"session_count": len(self._sessions), "session_ids": sorted(self._sessions.keys())}


@dataclass
class AppGlobalState(GlobalStateContract):
    queue_registry: TaskQueueRegistry = field(default_factory=TaskQueueRegistry)
    adapter_registry: ProviderAdapterRegistry = field(default_factory=ProviderAdapterRegistry)
    config_registry: ConfigTimeoutRegistry = field(default_factory=ConfigTimeoutRegistry)
    browser_registry: BrowserSessionRegistry = field(default_factory=BrowserSessionRegistry)

    async def enqueue(self, task: TaskEnvelope) -> None:
        await self.queue_registry.enqueue(task)

    async def dequeue(self, session_id: str) -> TaskEnvelope | None:
        return await self.queue_registry.dequeue(session_id)

    def register_adapter(self, provider_name: str, adapter: Any) -> None:
        self.adapter_registry.register_adapter(provider_name, adapter)

    def unregister_adapter(self, provider_name: str) -> None:
        self.adapter_registry.unregister_adapter(provider_name)

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "queue": self.queue_registry.snapshot_state(),
            "adapters": self.adapter_registry.snapshot_state(),
            "config": self.config_registry.snapshot_state(),
            "browser": self.browser_registry.snapshot_state(),
        }

    def restore_state(self, state: Mapping[str, Any]) -> None:
        if not self.validate_state(state):
            raise ValueError("Invalid app global state")
        self.queue_registry.restore_state(state["queue"])
        self.adapter_registry.restore_state(state["adapters"])
        self.config_registry.restore_state(state["config"])
        self.browser_registry.restore_state(state["browser"])

    def validate_state(self, state: Mapping[str, Any]) -> bool:
        required = ("queue", "adapters", "config", "browser")
        if not all(key in state for key in required):
            return False
        return (
            self.queue_registry.validate_state(state["queue"])
            and self.adapter_registry.validate_state(state["adapters"])
            and self.config_registry.validate_state(state["config"])
            and self.browser_registry.validate_state(state["browser"])
        )

    def health_report(self) -> dict[str, Any]:
        return {
            "queue": self.queue_registry.health_report(),
            "adapters": self.adapter_registry.health_report(),
            "config": self.config_registry.health_report(),
            "browser": self.browser_registry.health_report(),
        }


GLOBAL_STATE = AppGlobalState()
TASK_QUEUE = GLOBAL_STATE.queue_registry.queue
ADAPTER_REGISTRY = GLOBAL_STATE.adapter_registry
CONFIG_REGISTRY = GLOBAL_STATE.config_registry
BROWSER_SESSION_REGISTRY = GLOBAL_STATE.browser_registry

# Backward-compatible aliases for legacy global access points.
QUEUE = TASK_QUEUE
PROVIDER_ADAPTER_REGISTRY = ADAPTER_REGISTRY
SESSION_REGISTRY = BROWSER_SESSION_REGISTRY

__all__ = [
    "ADAPTER_REGISTRY",
    "AppGlobalState",
    "BROWSER_SESSION_REGISTRY",
    "CONFIG_REGISTRY",
    "GLOBAL_STATE",
    "GlobalStateContract",
    "PROVIDER_ADAPTER_REGISTRY",
    "QUEUE",
    "SESSION_REGISTRY",
    "TASK_QUEUE",
]
