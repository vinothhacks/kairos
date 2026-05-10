"""Shared pytest fixtures."""
from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from kairos.llm.mcp_client import StubLLMClient


@pytest.fixture(autouse=True)
def _force_stub_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """All unit tests use the stub LLM backend by default."""
    monkeypatch.setenv("KAIROS_LLM_BACKEND", "stub")
    monkeypatch.delenv("KAIROS_MCP_URL", raising=False)


@pytest.fixture
def stub_llm(tmp_path: Path) -> StubLLMClient:
    """Empty stub. Tests can pre-populate canned responses."""
    return StubLLMClient()


@pytest.fixture
def stub_llm_canned(tmp_path: Path, request: pytest.FixtureRequest) -> StubLLMClient:
    """Stub LLM seeded with canned responses from a dict the test parametrizes."""
    canned: dict[str, str] = getattr(request, "param", {})
    path = tmp_path / "stub.json"
    path.write_text(json.dumps(canned), encoding="utf-8")
    return StubLLMClient(stub_path=path)


@pytest.fixture
def project_root(tmp_path: Path) -> Iterator[Path]:
    """Chdir into a clean tmp dir and yield it as the project root."""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(cwd)
