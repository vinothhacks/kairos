"""Thin client over llm-mcp.

llm-mcp exposes tools as JSON-over-stdio (the MCP spec). For test ergonomics
in v0.1 we model the client as an abstract interface with two implementations:

- `StubLLMClient`: deterministic, in-process. Used by every unit test.
- `MCPLLMClient`: real client that subprocesses or HTTP-bridges to the running
  llm-mcp server. Used in e2e tests and by the CLI in production.

The CLI picks the implementation via `LLMClient.from_env()`:
- KAIROS_LLM_BACKEND=stub                -> StubLLMClient (loads canned responses from KAIROS_STUB_PATH)
- KAIROS_LLM_BACKEND=mcp (default)       -> MCPLLMClient

v0.2 changes:
- KAI-017: MCPLLMClient now retries 5xx + connect errors with exponential backoff.
- KAI-015: callers can inject a custom httpx transport for integration tests.
- KAI-026: StubLLMClient default reply no longer echoes the prompt.
"""
from __future__ import annotations

import json
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class LLMError(RuntimeError):
    """Anything that goes wrong inside the llm bridge."""


class MCPUnreachable(LLMError):
    """The llm-mcp server isn't running or didn't respond."""


@dataclass
class LLMResult:
    """Normalized result from any provider call."""

    text: str
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(ABC):
    """Abstract interface every kairos technique calls."""

    @abstractmethod
    def chatgpt_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult: ...

    @abstractmethod
    def claude_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult: ...

    @abstractmethod
    def search_web(self, query: str, *, provider: str = "claude") -> LLMResult: ...

    @staticmethod
    def from_env() -> LLMClient:
        backend = os.environ.get("KAIROS_LLM_BACKEND", "mcp").lower().strip()
        if backend == "stub":
            stub_path = os.environ.get("KAIROS_STUB_PATH")
            return StubLLMClient(stub_path=Path(stub_path) if stub_path else None)
        return MCPLLMClient()


@dataclass
class StubLLMClient(LLMClient):
    """Deterministic fake. Every test that does not need a live llm-mcp uses this."""

    stub_path: Path | None = None
    _canned: dict[str, str] = field(init=False, default_factory=dict)
    calls: list[tuple[str, str, str]] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        if self.stub_path and self.stub_path.exists():
            self._canned = json.loads(self.stub_path.read_text(encoding="utf-8"))

    def _reply_for(self, tool: str, message: str) -> str:
        # exact-key lookup first, then prefix lookup, then a deterministic default
        key = f"{tool}::{message[:80]}"
        if key in self._canned:
            return self._canned[key]
        for k, v in self._canned.items():
            if k.startswith(f"{tool}::") and message[:40] in k:
                return v
        # KAI-026: do NOT echo the prompt back; callers occasionally pipe replies
        # straight into render paths and prompt-leakage looks like a real answer.
        return f"[stub:{tool}] (no canned reply; seed via tests/conftest.py)"

    def chatgpt_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        self.calls.append(("chatgpt_send", conversation_id or "pending", message))
        return LLMResult(text=self._reply_for("chatgpt_send", message))

    def claude_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        self.calls.append(("claude_send", conversation_id or "pending", message))
        return LLMResult(text=self._reply_for("claude_send", message))

    def search_web(self, query: str, *, provider: str = "claude") -> LLMResult:
        self.calls.append(("search_web", provider, query))
        return LLMResult(text=self._reply_for(f"{provider}_search_web", query))


class MCPLLMClient(LLMClient):
    """Real client. v0.1 uses an HTTP shim hosted by llm-mcp on KAIROS_MCP_URL.

    For PyPI packaging simplicity v0.1 talks to llm-mcp via a tiny HTTP shim
    rather than via stdio MCP; the shim is provided by llm-mcp v0.2+ and
    exposes /tools/<name>/call. If the env var is unset and the shim isn't
    reachable, this client raises MCPUnreachable on first use.

    v0.2 (KAI-017) adds bounded retries + exponential backoff for transient
    failures (5xx, connect errors). 4xx responses are NOT retried: they
    indicate a permanent client error.
    """

    DEFAULT_MAX_ATTEMPTS = 3
    DEFAULT_BACKOFF_BASE = 0.5  # seconds

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float = 300.0,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ) -> None:
        self.base_url = (base_url or os.environ.get("KAIROS_MCP_URL", "http://localhost:8765")).rstrip("/")
        self.timeout_s = timeout_s
        self.max_attempts = max(1, int(max_attempts))
        self.backoff_base = max(0.0, float(backoff_base))
        self._transport: httpx.BaseTransport | None = None  # injected by integration tests

    def ping(self) -> bool:
        """Best-effort liveness probe used by `kairos doctor`. Returns False on error."""
        try:
            self._post("ping", {})
        except LLMError:
            return False
        return True

    def _make_httpx_client(self) -> httpx.Client:
        import httpx as _httpx

        if self._transport is not None:
            return _httpx.Client(transport=self._transport, timeout=self.timeout_s)
        return _httpx.Client(timeout=self.timeout_s)

    def _post(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as e:  # pragma: no cover
            raise LLMError("httpx is required; install kairos-agent[mcp]") from e
        url = f"{self.base_url}/tools/{tool}/call"
        last_err: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            with self._make_httpx_client() as client:
                try:
                    resp = client.post(url, json=payload)
                except httpx.HTTPError as e:
                    last_err = e
                    if attempt >= self.max_attempts:
                        raise MCPUnreachable(
                            f"llm-mcp at {self.base_url} is unreachable: {e}"
                        ) from e
                    self._sleep(attempt)
                    continue
            status = resp.status_code
            if status >= 500:
                last_err = LLMError(f"llm-mcp returned {status}: {resp.text[:300]}")
                if attempt >= self.max_attempts:
                    raise last_err
                self._sleep(attempt)
                continue
            if status >= 400:
                # KAI-017: 4xx is permanent, do not retry.
                raise LLMError(f"llm-mcp returned {status}: {resp.text[:300]}")
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                raise LLMError(
                    f"llm-mcp returned non-JSON body (first 200 chars): {resp.text[:200]!r}"
                ) from e
            if not isinstance(data, dict):
                raise LLMError(f"llm-mcp returned non-dict body: {type(data).__name__}")
            return data
        # Defensive: loop should always return or raise above.
        raise LLMError(f"llm-mcp call failed after {self.max_attempts} attempts: {last_err}")

    def _sleep(self, attempt: int) -> None:
        delay = self.backoff_base * (2 ** (attempt - 1))
        # tiny jitter so concurrent clients don't sync up
        delay += random.uniform(0.0, max(0.05, self.backoff_base / 4))
        time.sleep(delay)

    def chatgpt_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        cid = conversation_id or "pending"
        # llm-mcp expects an existing conversation; create lazily if pending.
        if cid == "pending":
            new = self._post("chatgpt_new_chat", {"title": "kairos"})
            cid = str(new.get("conversation_id", "pending"))
        out = self._post("chatgpt_send", {"conversation_id": cid, "message": message})
        return LLMResult(text=str(out.get("reply", "")), raw=out)

    def claude_send(self, message: str, *, conversation_id: str | None = None) -> LLMResult:
        cid = conversation_id or "pending"
        if cid == "pending":
            new = self._post("claude_new_chat", {"title": "kairos"})
            cid = str(new.get("conversation_id", "pending"))
        out = self._post("claude_send", {"conversation_id": cid, "message": message})
        return LLMResult(text=str(out.get("reply", "")), raw=out)

    def search_web(self, query: str, *, provider: str = "claude") -> LLMResult:
        tool = "claude_search_web" if provider == "claude" else "chatgpt_search_web"
        out = self._post(tool, {"query": query})
        return LLMResult(text=str(out.get("reply", "")), raw=out)
