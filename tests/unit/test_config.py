"""KAI-004 regression tests: .kairos/config.toml parser must be implemented."""
from __future__ import annotations

from pathlib import Path

import pytest

from kairos.utils.config import KairosConfig, load_config


def test_load_config_returns_defaults_when_no_file(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert isinstance(cfg, KairosConfig)
    assert cfg.llm_backend in {"mcp", "stub"}
    assert cfg.mcp_url.startswith("http")
    assert cfg.max_react_steps > 0
    assert cfg.rag_chunk_size > 0
    assert cfg.rag_top_k > 0
    assert cfg.stale_after_days > 0


def test_load_config_reads_toml_file(tmp_path: Path) -> None:
    state = tmp_path / ".kairos"
    state.mkdir()
    (state / "config.toml").write_text(
        '[llm]\nbackend = "stub"\nmcp_url = "http://example.com:9000"\n\n'
        "[runners]\nmax_react_steps = 12\nrag_chunk_size = 50\nrag_top_k = 4\n\n"
        "[lint]\nstale_after_days = 90\n",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.llm_backend == "stub"
    assert cfg.mcp_url == "http://example.com:9000"
    assert cfg.max_react_steps == 12
    assert cfg.rag_chunk_size == 50
    assert cfg.rag_top_k == 4
    assert cfg.stale_after_days == 90


def test_env_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / ".kairos"
    state.mkdir()
    (state / "config.toml").write_text('[llm]\nbackend = "mcp"\nmcp_url = "http://from-file:1"\n', encoding="utf-8")
    monkeypatch.setenv("KAIROS_LLM_BACKEND", "stub")
    monkeypatch.setenv("KAIROS_MCP_URL", "http://from-env:2")

    cfg = load_config(tmp_path)
    assert cfg.llm_backend == "stub"
    assert cfg.mcp_url == "http://from-env:2"


def test_load_config_handles_partial_file(tmp_path: Path) -> None:
    """Missing keys fall through to defaults; present keys are honored."""
    state = tmp_path / ".kairos"
    state.mkdir()
    (state / "config.toml").write_text("[runners]\nmax_react_steps = 9\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.max_react_steps == 9
    assert cfg.rag_top_k > 0  # default still applies


def test_load_config_reads_bom_wiki_selector_and_sources(tmp_path: Path) -> None:
    """KAI2-012/KAI2-023: BOM files and documented tables are parsed."""
    state = tmp_path / ".kairos"
    state.mkdir()
    (state / "config.toml").write_bytes(
        b'\xef\xbb\xbf[llm]\nbackend = "STUB"\n\n'
        b"[wiki]\nstale_after_days = 7\nauto_save_query_answers = true\n\n"
        b'[selector]\ndefault_technique = "react"\nrequire_runner = false\n\n'
        b'[sources]\nnotes = "./raw/notes"\n'
    )

    cfg = load_config(tmp_path)
    assert cfg.config_had_bom is True
    assert cfg.llm_backend == "stub"
    assert cfg.stale_after_days == 7
    assert cfg.auto_save_query_answers is True
    assert cfg.default_technique == "react"
    assert cfg.require_runner is False
    assert cfg.source_paths == {"notes": "./raw/notes"}
