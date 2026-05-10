"""StubLLMClient behavior tests."""
from __future__ import annotations

import json
from pathlib import Path

from kairos.llm.mcp_client import LLMClient, StubLLMClient


def test_stub_returns_canned_response_by_exact_key(tmp_path: Path) -> None:
    canned = {"claude_send::What is RAG?": "Retrieval Augmented Generation"}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(canned), encoding="utf-8")
    stub = StubLLMClient(stub_path=path)
    out = stub.claude_send("What is RAG?")
    assert "Retrieval Augmented Generation" in out.text


def test_stub_falls_back_on_unknown_key() -> None:
    stub = StubLLMClient()
    out = stub.chatgpt_send("Some random prompt")
    assert "stub:chatgpt_send" in out.text
    assert len(stub.calls) == 1


def test_stub_records_calls() -> None:
    stub = StubLLMClient()
    stub.claude_send("a")
    stub.chatgpt_send("b")
    stub.search_web("c", provider="claude")
    assert [c[0] for c in stub.calls] == ["claude_send", "chatgpt_send", "search_web"]


def test_from_env_returns_stub_when_requested(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("KAIROS_LLM_BACKEND", "stub")
    client = LLMClient.from_env()
    assert isinstance(client, StubLLMClient)
