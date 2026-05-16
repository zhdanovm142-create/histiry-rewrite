from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.providers.base.base_provider_adapter import BaseProviderAdapter


AdapterBuilder = Callable[[Any], BaseProviderAdapter]


class ProviderAdapterRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, AdapterBuilder] = {}

    def register(self, provider: str, builder: AdapterBuilder) -> None:
        self._builders[provider] = builder

    def create(self, provider: str, page: Any) -> BaseProviderAdapter:
        try:
            return self._builders[provider](page)
        except KeyError as exc:
            raise ValueError(f"Unknown provider: {provider}") from exc

