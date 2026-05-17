"""Deterministic in-process LLM provider used by tests."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from kairos.llm.providers.base import LLMClient, LLMResult


@dataclass
class StubLLMClient(LLMClient):
    """Deterministic fake. Every test that does not need a live provider uses this."""

    stub_path: Path | None = None
    _canned: dict[str, str] = field(init=False, default_factory=dict)
    calls: list[tuple[str, str, str]] = field(init=False, default_factory=list)

    name = "stub"

    def __post_init__(self) -> None:
        if self.stub_path and self.stub_path.exists():
            self._canned = json.loads(self.stub_path.read_text(encoding="utf-8-sig"))

    def _reply_for(self, tool: str, message: str) -> str:
        # Exact-key lookup first, then prefix lookup, then a deterministic default.
        key = f"{tool}::{message[:80]}"
        if key in self._canned:
            return self._canned[key]
        for k, v in self._canned.items():
            if k.startswith(f"{tool}::") and message[:40] in k:
                return v
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
