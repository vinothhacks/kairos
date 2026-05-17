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
    # Pre-populate tiny seed concept pages so query/run have a real top-3.
    for slug, title, body in [
        ("rag", "RAG", "Retrieval augmented generation."),
        ("react", "ReAct", "Tool-using reasoning loop."),
        ("reflexion", "Reflexion", "Critique and revise loop."),
    ]:
        (tmp_path / "wiki" / "concepts" / f"{slug}.md").write_text(
            f"---\ntitle: {title}\ntype: concept\ncreated: 2026-04-01\nupdated: 2026-04-01\nconfidence: high\nhas_runner: true\n---\n\n## Summary\n\n{body}\n",
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
    assert "stub backend, no network" in result.stdout
    assert "llm-mcp" not in result.stdout


def test_doctor_reports_removed_mcp_backend(runner: CliRunner) -> None:
    """v0.4: the old llm-mcp backend is a migration error, not a liveness probe."""
    result = runner.invoke(app, ["doctor"], env={"KAIROS_LLM_BACKEND": "mcp"})

    assert result.exit_code == 0
    assert "migration required" in result.stdout.lower()
    assert "ollama" in result.stdout


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


def test_run_json_stdout_is_parseable(initialized_project: Path, runner: CliRunner) -> None:
    """KAI2-003/KAI2-021: --json stdout must contain only JSON."""
    result = runner.invoke(
        app,
        ["run", "Search the docs for caching", "--project", str(initialized_project), "--json"],
        env={"KAIROS_LLM_BACKEND": "stub"},
    )
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout)
    assert payload["task"] == "Search the docs for caching"
    assert payload["technique"] in {"rag", "react", "reflexion"}


def test_run_json_dry_stdout_is_parseable(initialized_project: Path, runner: CliRunner) -> None:
    """KAI2-004/KAI2-021: --json --dry must emit candidates as JSON, not a Rich table."""
    result = runner.invoke(
        app,
        ["run", "Search the docs for caching", "--project", str(initialized_project), "--json", "--dry"],
        env={"KAIROS_LLM_BACKEND": "stub"},
    )
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout)
    assert payload["task"] == "Search the docs for caching"
    assert [row["rank"] for row in payload["candidates"]] == [1, 2, 3]


def test_lint_honors_stale_after_days_config(initialized_project: Path, runner: CliRunner) -> None:
    """KAI2-005: lint must consume .kairos/config.toml, not just doctor."""
    cfg = initialized_project / ".kairos" / "config.toml"
    cfg.write_text("[lint]\nstale_after_days = 0\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["lint", "--project", str(initialized_project)],
        env={"KAIROS_LLM_BACKEND": "stub"},
    )
    assert result.exit_code == 0, result.stdout
    assert "stale" in result.stdout.lower()


def test_feedback_unknown_run_id_is_user_friendly(initialized_project: Path, runner: CliRunner) -> None:
    """KAI2-006: unknown run ids should not leak sqlite3.IntegrityError."""
    result = runner.invoke(
        app,
        [
            "feedback",
            "99999",
            "--rating",
            "5",
            "--note",
            "missing run",
            "--project",
            str(initialized_project),
        ],
    )

    assert result.exit_code == 1
    assert "run id 99999 not found" in result.stdout.lower()
    assert "IntegrityError" not in result.stdout
    assert "Traceback" not in result.stdout
