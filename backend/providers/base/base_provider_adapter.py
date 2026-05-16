from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel, Field


class LocateInputRequest(BaseModel):
    selector: str | None = None
    timeout_ms: int = 30_000


class LocateInputResult(BaseModel):
    found: bool
    selector: str | None = None
    details: str | None = None


class SendPromptRequest(BaseModel):
    prompt: str
    metadata: dict[str, str] = Field(default_factory=dict)


class SendPromptResult(BaseModel):
    accepted: bool
    request_id: str | None = None


class StreamWaitRequest(BaseModel):
    request_id: str | None = None
    timeout_ms: int = 120_000


class StreamWaitResult(BaseModel):
    completed: bool
    elapsed_ms: int


class ExtractResponseResult(BaseModel):
    text: str
    request_id: str | None = None


class ExtractMarkdownResult(BaseModel):
    markdown: str


class GenerationState(BaseModel):
    generating: bool
    reason: str | None = None


class ProviderError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class DetectErrorsResult(BaseModel):
    errors: list[ProviderError]


class SupportsProviderMetadata(Protocol):
    provider_name: str


class BaseProviderAdapter(ABC):
    """Provider adapter contract for provider-specific UI/API automation."""

    @abstractmethod
    async def locate_input(self, request: LocateInputRequest) -> LocateInputResult:
        raise NotImplementedError

    @abstractmethod
    async def send_prompt(self, request: SendPromptRequest) -> SendPromptResult:
        raise NotImplementedError

    @abstractmethod
    async def wait_stream_complete(self, request: StreamWaitRequest) -> StreamWaitResult:
        raise NotImplementedError

    @abstractmethod
    async def extract_response(self) -> ExtractResponseResult:
        raise NotImplementedError

    @abstractmethod
    async def extract_markdown(self) -> ExtractMarkdownResult:
        raise NotImplementedError

    @abstractmethod
    async def is_generating(self) -> GenerationState:
        raise NotImplementedError

    @abstractmethod
    async def detect_errors(self) -> DetectErrorsResult:
        raise NotImplementedError
