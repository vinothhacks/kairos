"""Generic OpenAI-compatible provider."""
from __future__ import annotations

import os

import httpx

from kairos.llm.providers.openai import OpenAIClient


class OpenAICompatClient(OpenAIClient):
    """OpenAI-compatible client for LM Studio, vLLM, Ollama OpenAI mode, etc."""

    name = "openai_compat"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float = 300.0,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved_base_url = base_url or os.environ.get("KAIROS_LLM_BASE_URL")
        if not resolved_base_url:
            from kairos.llm.providers.base import LLMError

            raise LLMError("KAIROS_LLM_BASE_URL is required for KAIROS_LLM_BACKEND=openai_compat")
        super().__init__(
            api_key=api_key or os.environ.get("KAIROS_LLM_API_KEY") or "local",
            model=model or os.environ.get("KAIROS_LLM_MODEL", "local-model"),
            base_url=resolved_base_url,
            timeout_s=timeout_s,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            transport=transport,
        )
