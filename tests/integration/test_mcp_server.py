"""MCP server integration tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from kairos.mcp.server import build_mcp_server
from kairos.wiki.init import init_project

pytestmark = pytest.mark.integration


def _project_with_seed(tmp_path: Path) -> Path:
    init_project(tmp_path, with_seed=False)
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


def test_mcp_server_registers_expected_tools() -> None:
    server = build_mcp_server()
    tools = anyio.run(server.list_tools)
    names = {tool.name for tool in tools}

    assert {
        "kairos.select_technique",
        "kairos.run_technique",
        "kairos.query_wiki",
        "kairos.lint_wiki",
        "kairos.ingest_source",
        "kairos.history",
        "kairos.feedback",
    } <= names


def test_mcp_select_technique_tool_returns_ranking(tmp_path: Path) -> None:
    project = _project_with_seed(tmp_path)
    server = build_mcp_server()

    structured = _call(server, "kairos.select_technique", {"task": "Search docs with retrieval", "project": str(project)})

    assert structured["task"] == "Search docs with retrieval"
    assert structured["choices"]


def test_mcp_server_tools_round_trip_expected_shapes(tmp_path: Path) -> None:
    project = _project_with_seed(tmp_path)
    raw = project / "raw" / "note.md"
    raw.write_text("# Cache notes\n\nUse retrieval for cache docs.\n", encoding="utf-8")
    server = build_mcp_server()

    dry_run = _call(
        server,
        "kairos.run_technique",
        {"task": "Search cache docs", "project": str(project), "dry": True},
    )
    assert dry_run["dry"] is True
    assert dry_run["technique"]

    query = _call(
        server,
        "kairos.query_wiki",
        {"question": "When should I use RAG?", "project": str(project)},
    )
    assert query["question"] == "When should I use RAG?"
    assert "answer" in query

    lint = _call(server, "kairos.lint_wiki", {"project": str(project)})
    assert cast(int, lint["pages_scanned"]) >= 3
    assert "findings" in lint

    ingest = _call(
        server,
        "kairos.ingest_source",
        {"source_path": str(raw), "project": str(project)},
    )
    assert ingest["raw_path"]
    assert ingest["source_page"]

    run = _call(
        server,
        "kairos.run_technique",
        {"task": "Search cache docs", "project": str(project), "technique": "rag"},
    )
    run_id = cast(int, run["run_id"])
    assert run_id > 0
    assert run["status"] == "ok"

    history = _call(server, "kairos.history", {"project": str(project), "limit": 5})
    assert history["runs"]

    feedback = _call(
        server,
        "kairos.feedback",
        {"project": str(project), "run_id": run_id, "rating": 5, "note": "mcp ok"},
    )
    assert feedback["run_id"] == run_id
    assert feedback["rating"] == 5


def _call(server: Any, name: str, arguments: dict[str, object]) -> dict[str, object]:
    result = anyio.run(server.call_tool, name, arguments)
    _content, structured = result
    assert isinstance(structured, dict)
    return structured
