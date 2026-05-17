"""Anthropic Claude provider."""
from __future__ import annotations

import os
from typing import Any

import httpx

from kairos.llm.providers._http import RetryingHTTPClient
from kairos.llm.providers.base import LLMClient, LLMError, LLMResult


class AnthropicClient(LLMClient):
    """Direct client for Anthropic's messages API."""

    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.anthropic.com/v1",
        timeout_s: float = 300.0,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is required for KAIROS_LLM_BACKEND=anthropic")
        self.model = model or os.environ.get("KAIROS_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        self._http = RetryingHTTPClient(
            base_url,
            timeout_s=timeout_s,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            transport=transport,
        )

    def ping(self) -> bool:
        try:
            # Anthropic has no cheap unauthenticated ping; a tiny messages call verifies wiring.
            self._chat("Reply with ok.")
        except LLMError:
            return False
        return True

    def chatgpt_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        return self._chat(message)

    def claude_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        return self._chat(message)

    def search_web(self, query: str, *, provider: str = "claude") -> LLMResult:
        return self._chat(f"Answer this query as directly as possible: {query}")

    def _chat(self, message: str) -> LLMResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": message}],
        }
        data = self._http.request_json(
            "POST",
            "/messages",
            json_body=payload,
            headers=self._headers(),
        )
        content = data.get("content")
        if not isinstance(content, list):
            raise LLMError("anthropic returned invalid content payload")
        texts = [
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        return LLMResult(text="\n".join(texts), raw=data)

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": str(self.api_key),
            "anthropic-version": "2023-06-01",
        }
