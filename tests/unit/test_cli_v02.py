"""KAI-007 / KAI-009 / KAI-011 / KAI-032 CLI regression tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kairos.cli import app
from kairos.wiki.init import init_project


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def initialized_project(tmp_path: Path) -> Path:
    init_project(tmp_path, with_seed=False)
    # Pre-populate a tiny seed concept page so query/run don't error.
    (tmp_path / "wiki" / "concepts" / "rag.md").write_text(
        "---\ntitle: RAG\ntype: concept\ncreated: 2026-04-01\nupdated: 2026-04-01\nconfidence: high\nhas_runner: true\n---\n\n## Summary\n\nRetrieval augmented generation.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_query_preserves_wikilinks_in_output(initialized_project: Path, runner: CliRunner, tmp_path: Path) -> None:
    """KAI-007 / KAI-032: [[wikilinks]] in LLM output must NOT be eaten by Rich markup."""
    canned = {
        "claude_send::You are answering a question grounded in this wiki": "Use [[react]] when you need tools, otherwise [[rag]].\n\n## Sources\n- [[react]]\n- [[rag]]",
    }
    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps(canned), encoding="utf-8")

    result = runner.invoke(
        app,
        ["query", "When should I use ReAct?", "--project", str(initialized_project)],
        env={"KAIROS_LLM_BACKEND": "stub", "KAIROS_STUB_PATH": str(stub_path)},
    )
    assert result.exit_code == 0, result.stdout
    assert "[[react]]" in result.stdout, "wikilinks were stripped by Rich markup"
    assert "[[rag]]" in result.stdout


def test_doctor_runs_without_error(initialized_project: Path, runner: CliRunner) -> None:
    """KAI-011: kairos doctor must succeed in a stubbed env (probe is best-effort)."""
    result = runner.invoke(
        app,
        ["doctor", "--project", str(initialized_project)] if False else ["doctor"],
        env={"KAIROS_LLM_BACKEND": "stub"},
    )
    # The CLI doesn't take --project on doctor today; just exercise default path.
    assert result.exit_code == 0
    assert "kairos" in result.stdout.lower() or "doctor" in result.stdout.lower()


def test_query_command_does_not_crash_on_lint_severity_label(
    initialized_project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    """Sanity: lint table renders severity columns without Rich crashes."""
    stub_path = tmp_path / "stub.json"
    stub_path.write_text(
        json.dumps({"claude_send::You are linting a wiki": "- [low] no findings | - | wiki looks consistent"}),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["lint", "--project", str(initialized_project)],
        env={"KAIROS_LLM_BACKEND": "stub", "KAIROS_STUB_PATH": str(stub_path)},
    )
    assert result.exit_code == 0
