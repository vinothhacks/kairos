"""Direct LLM provider factory."""
from __future__ import annotations

import os

from kairos.llm.providers.anthropic import AnthropicClient
from kairos.llm.providers.base import LLMClient, LLMError, LLMResult, MCPUnreachable
from kairos.llm.providers.ollama import OllamaClient
from kairos.llm.providers.openai import OpenAIClient
from kairos.llm.providers.openai_compat import OpenAICompatClient
from kairos.llm.providers.stub import StubLLMClient


def from_env() -> LLMClient:
    """Create the configured LLM provider from environment variables."""
    backend = os.environ.get("KAIROS_LLM_BACKEND", "stub").lower().strip()
    if backend == "stub":
        stub_path = os.environ.get("KAIROS_STUB_PATH")
        from pathlib import Path

        return StubLLMClient(stub_path=Path(stub_path) if stub_path else None)
    if backend == "ollama":
        return OllamaClient()
    if backend == "openai":
        return OpenAIClient()
    if backend == "anthropic":
        return AnthropicClient()
    if backend == "openai_compat":
        return OpenAICompatClient()
    if backend == "mcp":
        raise LLMError(
            "llm-mcp backend was removed in kairos v0.4. Use KAIROS_LLM_BACKEND="
            "ollama, openai, anthropic, openai_compat, or stub. See docs/UPGRADING.md."
        )
    raise LLMError(f"unknown KAIROS_LLM_BACKEND={backend!r}")


__all__ = [
    "AnthropicClient",
    "LLMClient",
    "LLMError",
    "LLMResult",
    "MCPUnreachable",
    "OllamaClient",
    "OpenAIClient",
    "OpenAICompatClient",
    "StubLLMClient",
    "from_env",
]
