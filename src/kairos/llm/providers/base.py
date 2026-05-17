"""Shared LLM provider contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMError(RuntimeError):
    """Anything that goes wrong inside an LLM provider."""


class MCPUnreachable(LLMError):
    """Compatibility alias for the old llm-mcp unreachable error."""


@dataclass
class LLMResult:
    """Normalized result from any provider call."""

    text: str
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(ABC):
    """Abstract interface every kairos technique calls."""

    name = "base"
    supports_web_search = False

    @abstractmethod
    def chatgpt_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult: ...

    @abstractmethod
    def claude_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult: ...

    @abstractmethod
    def search_web(self, query: str, *, provider: str = "claude") -> LLMResult: ...

    def ping(self) -> bool:
        """Best-effort liveness probe used by `kairos doctor`."""
        return True

    @staticmethod
    def from_env() -> LLMClient:
        from kairos.llm.providers import from_env

        return from_env()
