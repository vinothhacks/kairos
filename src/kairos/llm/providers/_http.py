"""Small retrying JSON-over-HTTP helper shared by direct providers."""
from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

import httpx

from kairos.llm.providers.base import LLMError, MCPUnreachable


@dataclass
class RetryingHTTPClient:
    """HTTP client with bounded retries for transient provider failures."""

    base_url: str
    timeout_s: float = 300.0
    max_attempts: int = 3
    backoff_base: float = 0.5
    transport: httpx.BaseTransport | None = None

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.max_attempts = max(1, int(self.max_attempts))
        self.backoff_base = max(0.0, float(self.backoff_base))

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_err: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                with self._make_client() as client:
                    response = client.request(method, url, json=json_body, headers=headers)
            except httpx.HTTPError as exc:
                last_err = exc
                if attempt >= self.max_attempts:
                    raise MCPUnreachable(f"provider at {self.base_url} is unreachable: {exc}") from exc
                self._sleep(attempt)
                continue

            if response.status_code >= 500:
                last_err = LLMError(
                    f"provider at {self.base_url} returned {response.status_code}: "
                    f"{response.text[:300]}"
                )
                if attempt >= self.max_attempts:
                    raise last_err
                self._sleep(attempt)
                continue
            if response.status_code >= 400:
                raise LLMError(
                    f"provider at {self.base_url} returned {response.status_code}: "
                    f"{response.text[:300]}"
                )
            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                raise LLMError(
                    f"provider at {self.base_url} returned non-JSON body "
                    f"(first 200 chars): {response.text[:200]!r}"
                ) from exc
            if not isinstance(data, dict):
                raise LLMError(
                    f"provider at {self.base_url} returned non-dict body: "
                    f"{type(data).__name__}"
                )
            return data

        raise LLMError(f"provider call failed after {self.max_attempts} attempts: {last_err}")

    def _make_client(self) -> httpx.Client:
        if self.transport is not None:
            return httpx.Client(transport=self.transport, timeout=self.timeout_s)
        return httpx.Client(timeout=self.timeout_s)

    def _sleep(self, attempt: int) -> None:
        delay = self.backoff_base * (2 ** (attempt - 1))
        jitter_max = max(0.05, self.backoff_base / 4)
        delay += jitter_max * (secrets.randbelow(1000) / 1000.0)
        time.sleep(delay)
