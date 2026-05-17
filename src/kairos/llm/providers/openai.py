"""OpenAI ChatGPT provider."""
from __future__ import annotations

import os
from typing import Any

import httpx

from kairos.llm.providers._http import RetryingHTTPClient
from kairos.llm.providers.base import LLMClient, LLMError, LLMResult


class OpenAIClient(LLMClient):
    """Direct client for OpenAI's chat completions API."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 300.0,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is required for KAIROS_LLM_BACKEND=openai")
        self.model = model or os.environ.get("KAIROS_OPENAI_MODEL", "gpt-4o-mini")
        self._http = RetryingHTTPClient(
            base_url,
            timeout_s=timeout_s,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            transport=transport,
        )

    def ping(self) -> bool:
        try:
            self._http.request_json("GET", "/models", headers=self._headers())
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
            "messages": [{"role": "user", "content": message}],
        }
        data = self._http.request_json(
            "POST",
            "/chat/completions",
            json_body=payload,
            headers=self._headers(),
        )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMError("openai returned no choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise LLMError("openai returned invalid choice payload")
        message_payload = first.get("message", {})
        if not isinstance(message_payload, dict):
            raise LLMError("openai returned invalid message payload")
        return LLMResult(text=str(message_payload.get("content", "")), raw=data)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
