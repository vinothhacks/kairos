"""Stdio MCP server exposing kairos tools."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kairos.llm.providers import LLMClient


def build_mcp_server() -> Any:
    """Build the FastMCP server without starting stdio transport."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised by packaging smoke
        raise RuntimeError("Install kairos-agent[mcp-server] to use `kairos mcp serve`.") from exc

    server = FastMCP(
        name="kairos",
        instructions="Use kairos to select, run, query, lint, ingest, and inspect agent techniques.",
    )

    @server.tool(name="kairos.select_technique", structured_output=True)
    def select_technique_tool(task: str, project: str | None = None) -> dict[str, Any]:
        from kairos.selector import select_technique
        from kairos.utils.config import load_config

        root = _project_root(project)
        cfg = load_config(root)
        choices = select_technique(
            task=task,
            project_root=root,
            llm=LLMClient.from_env(),
            require_runner=cfg.require_runner,
            tie_break_threshold=cfg.tie_break_threshold,
            default_technique=cfg.default_technique,
        )
        return {"task": task, "choices": [_choice_to_dict(choice) for choice in choices]}

    @server.tool(name="kairos.run_technique", structured_output=True)
    def run_technique_tool(
        task: str,
        technique: str = "auto",
        project: str | None = None,
        dry: bool = False,
    ) -> dict[str, Any]:
        from kairos.runners import dispatch
        from kairos.selector import select_technique

        root = _project_root(project)
        llm = LLMClient.from_env()
        selected_by = "user"
        selector_score: float | None = None
        chosen = technique
        choices: list[Any] = []
        if technique == "auto":
            choices = select_technique(task=task, project_root=root, llm=llm)
            chosen = choices[0].technique
            selected_by = "selector"
            selector_score = float(choices[0].score)
        if dry:
            return {
                "task": task,
                "technique": chosen,
                "dry": True,
                "choices": [_choice_to_dict(choice) for choice in choices],
            }
        result = dispatch(
            chosen,
            task=task,
            project_root=root,
            llm=llm,
            selected_by=selected_by,
            selector_score=selector_score,
        )
        return {
            "run_id": result.run_id,
            "technique": result.technique,
            "task": result.task,
            "status": result.status,
            "duration_ms": result.duration_ms,
            "answer": result.answer,
            "error": result.error,
        }

    @server.tool(name="kairos.query_wiki", structured_output=True)
    def query_wiki_tool(question: str, project: str | None = None, save: bool = False) -> dict[str, Any]:
        from kairos.wiki.query import query_wiki

        root = _project_root(project)
        result = query_wiki(question, project_root=root, llm=LLMClient.from_env(), save_to_wiki=save)
        return {
            "question": result.question,
            "answer": result.answer,
            "pages_read": [str(path) for path in result.pages_read],
            "saved_to": str(result.saved_to) if result.saved_to else None,
        }

    @server.tool(name="kairos.lint_wiki", structured_output=True)
    def lint_wiki_tool(project: str | None = None) -> dict[str, Any]:
        from kairos.utils.config import load_config
        from kairos.wiki.lint import lint_wiki

        root = _project_root(project)
        cfg = load_config(root)
        result = lint_wiki(
            project_root=root,
            llm=LLMClient.from_env(),
            stale_after_days=cfg.stale_after_days,
        )
        return {
            "pages_scanned": result.pages_scanned,
            "report_path": str(result.report_path),
            "findings": [
                {
                    "severity": finding.severity,
                    "kind": finding.kind,
                    "page": finding.page,
                    "note": finding.note,
                    "provenance": finding.provenance,
                }
                for finding in result.findings
            ],
        }

    @server.tool(name="kairos.ingest_source", structured_output=True)
    def ingest_source_tool(source_path: str, project: str | None = None) -> dict[str, Any]:
        from kairos.wiki.ingest import ingest_file

        root = _project_root(project)
        result = ingest_file(Path(source_path), project_root=root, llm=LLMClient.from_env())
        return {
            "title": result.title,
            "raw_path": str(result.raw_path),
            "source_page": str(result.source_page),
            "writes": [str(path) for path in result.all_writes],
        }

    @server.tool(name="kairos.history", structured_output=True)
    def history_tool(project: str | None = None, limit: int = 20) -> dict[str, Any]:
        from kairos.memory.db import Database
        from kairos.utils.paths import WikiPaths

        root = _project_root(project)
        rows = Database(path=WikiPaths(root=root).db).list_runs(limit=limit)
        return {"runs": [_row_to_dict(row) for row in rows]}

    @server.tool(name="kairos.feedback", structured_output=True)
    def feedback_tool(
        run_id: int,
        rating: int,
        note: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        from kairos.memory.db import Database
        from kairos.utils.paths import WikiPaths

        root = _project_root(project)
        db = Database(path=WikiPaths(root=root).db)
        with db.conn() as conn:
            exists = conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
        if exists is None:
            raise ValueError(f"run id {run_id} not found")
        feedback_id = db.insert_feedback(run_id=run_id, rating=rating, note=note)
        return {"feedback_id": feedback_id, "run_id": run_id, "rating": rating}

    return server


def run_stdio_server() -> None:
    """Run kairos as a stdio MCP server."""
    build_mcp_server().run("stdio")


def _project_root(project: str | None) -> Path:
    from kairos.utils.paths import resolve_root

    return Path(project).resolve() if project else resolve_root().resolve()


def _choice_to_dict(choice: Any) -> dict[str, Any]:
    return {
        "technique": choice.technique,
        "score": float(choice.score),
        "rationale": choice.rationale,
        "page": str(choice.page) if choice.page else None,
    }


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
