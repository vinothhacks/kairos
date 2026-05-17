"""Local Ollama provider."""
from __future__ import annotations

import os
from typing import Any

import httpx

from kairos.llm.providers._http import RetryingHTTPClient
from kairos.llm.providers.base import LLMClient, LLMError, LLMResult


class OllamaClient(LLMClient):
    """Direct client for a local Ollama runtime."""

    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 300.0,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or os.environ.get("KAIROS_OLLAMA_URL", "http://localhost:11434")
        self.model = model or os.environ.get("KAIROS_OLLAMA_MODEL", "llama3.1")
        self._http = RetryingHTTPClient(
            self.base_url,
            timeout_s=timeout_s,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            transport=transport,
        )

    def ping(self) -> bool:
        try:
            self._http.request_json("GET", "/api/tags")
        except LLMError:
            return False
        return True

    def chatgpt_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        return self._chat(message, conversation_id=conversation_id)

    def claude_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        return self._chat(message, conversation_id=conversation_id)

    def search_web(self, query: str, *, provider: str = "claude") -> LLMResult:
        return self._chat(f"Search or reason from available knowledge, then answer: {query}")

    def _chat(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "stream": False,
        }
        data = self._http.request_json("POST", "/api/chat", json_body=payload)
        reply = data.get("message", {})
        if not isinstance(reply, dict):
            raise LLMError("ollama returned invalid message payload")
        return LLMResult(text=str(reply.get("content", "")), raw=data)
