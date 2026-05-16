from backend.providers.deepseek.deepseek_adapter import DeepSeekAdapter
from backend.providers.qwen.qwen_adapter import QwenAdapter
from backend.providers.registry import ProviderAdapterRegistry


def create_default_registry() -> ProviderAdapterRegistry:
    registry = ProviderAdapterRegistry()
    registry.register("qwen", lambda page: QwenAdapter(page))
    registry.register("deepseek", lambda page: DeepSeekAdapter(page))
    return registry
