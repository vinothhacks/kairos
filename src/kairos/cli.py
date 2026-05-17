"""kairos CLI - Typer entry point.

Subcommands:
    init      bootstrap a new kairos project
    ingest    ingest a source file into the wiki
    query     ask a question against the wiki
    lint      health-check the wiki
    run       pick + execute a technique for a task
    feedback  rate a previous run (writes to .kairos/kairos.db)
    doctor    print env diagnostics + probe the configured LLM provider
    version   print the package version

Every command is a thin wrapper over a function in src/kairos/wiki/ or
src/kairos/runners/. The CLI does Rich formatting and error handling only.
"""
from __future__ import annotations

import json as _json
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

from kairos import __version__
from kairos.llm.providers import LLMClient, LLMError, MCPUnreachable
from kairos.utils.config import load_config
from kairos.utils.paths import WikiPaths, resolve_root
from kairos.wiki.init import init_project

if TYPE_CHECKING:
    from kairos.selector import TechniqueChoice

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="kairos - Stop guessing. Run the right pattern. A CLI for executable agent knowledge.",
    rich_markup_mode=None,
)
mcp_app = typer.Typer(
    add_completion=False,
    help="Run kairos as a stdio MCP server for Cursor, Claude Desktop, and other clients.",
)
app.add_typer(mcp_app, name="mcp")
console = Console()


@app.command()
def version() -> None:
    """Print the kairos version."""
    console.print(f"kairos [bold cyan]{__version__}[/]")


@mcp_app.command("serve")
def mcp_serve() -> None:
    """Serve kairos tools over stdio MCP."""
    try:
        from kairos.mcp.server import run_stdio_server
    except RuntimeError as exc:
        console.print(f"[red]error[/]: {exc}")
        raise typer.Exit(2) from exc
    run_stdio_server()


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Where to create the project."),
    force: bool = typer.Option(False, "--force", help="Overwrite AGENTS.md and seed pages if they exist."),
    no_seed: bool = typer.Option(False, "--no-seed", help="Skip copying the bundled seed concept pages."),
) -> None:
    """Bootstrap a new kairos project (AGENTS.md, raw/, wiki/, outputs/)."""
    result = init_project(path, force=force, with_seed=not no_seed)
    table = Table(title=f"kairos init -> {path.resolve()}")
    table.add_column("status")
    table.add_column("path")
    for p in result.created:
        table.add_row("[green]created[/]", str(p.relative_to(path.resolve())))
    for p in result.skipped:
        table.add_row("[yellow]skipped[/]", str(p.relative_to(path.resolve())))
    console.print(table)
    console.print(
        f"[dim]seeded {result.seeded_concepts} concept page(s) into wiki/concepts/[/]"
    )


@app.command()
def ingest(
    source: Path = typer.Argument(..., help="Path to the source file to ingest."),
    project: Path = typer.Option(None, "--project", "-p", help="Project root. Defaults to walking up to find AGENTS.md."),
    max_updates: int = typer.Option(15, "--max-updates", help="Cap on cascading concept-page updates."),
) -> None:
    """Ingest a source file: write source summary + cascade concept-page updates."""
    from kairos.wiki.ingest import ingest_file

    root = (project or resolve_root()).resolve()
    if not source.exists():
        console.print(f"[red]error[/]: source file not found: {source}")
        raise typer.Exit(2)

    llm = LLMClient.from_env()
    try:
        result = ingest_file(source, project_root=root, llm=llm, max_concept_updates=max_updates)
    except MCPUnreachable as e:
        console.print(f"[red]llm provider unreachable[/]: {e}")
        raise typer.Exit(3) from e
    except LLMError as e:
        # KAI-009: catch LLMError generically so 5xx / non-JSON / 4xx surface clean.
        console.print(f"[red]llm error[/]: {e}")
        raise typer.Exit(3) from e
    except UnicodeDecodeError as e:
        # KAI-023: binary or wrong-encoding source files hit a clean error path.
        console.print(f"[red]error[/]: source file is not valid UTF-8: {e}")
        raise typer.Exit(2) from e

    console.print(f"ingested: {result.title}", markup=False)
    table = Table(title=f"writes ({len(result.all_writes)})")
    table.add_column("kind")
    table.add_column("path")
    table.add_row("raw", str(result.raw_path.relative_to(root)))
    table.add_row("source", str(result.source_page.relative_to(root)))
    for p in result.concept_pages_created:
        table.add_row("concept (new)", str(p.relative_to(root)))
    for p in result.concept_pages_updated:
        table.add_row("concept (upd)", str(p.relative_to(root)))
    console.print(table)


@app.command()
def query(
    question: str = typer.Argument(..., help="The question to ask the wiki."),
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
    save: bool = typer.Option(False, "--save-to-wiki", help="File the answer back as a new wiki page."),
) -> None:
    """Ask a question against the wiki. Answer cites pages with [[wikilinks]]."""
    from kairos.wiki.query import query_wiki

    root = (project or resolve_root()).resolve()
    cfg = load_config(root)
    llm = LLMClient.from_env()
    try:
        result = query_wiki(
            question,
            project_root=root,
            llm=llm,
            save_to_wiki=save or cfg.auto_save_query_answers,
        )
    except MCPUnreachable as e:
        console.print(f"[red]llm provider unreachable[/]: {e}")
        raise typer.Exit(3) from e
    except LLMError as e:
        console.print(f"[red]llm error[/]: {e}")
        raise typer.Exit(3) from e

    console.rule(f"[bold cyan]Q[/]: {question}")
    # KAI-007: do NOT let Rich interpret [[wikilinks]] / brackets in the LLM reply.
    console.print(result.answer, markup=False)
    console.rule(f"[dim]read {len(result.pages_read)} page(s)[/]")
    if result.saved_to:
        console.print(f"[green]saved to wiki[/]: {result.saved_to.relative_to(root)}", markup=True)


@app.command()
def lint(
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
    fix: bool = typer.Option(False, "--fix", help="(v0.2) Apply suggested edits."),
) -> None:
    """Health-check the wiki: contradictions, orphans, stale claims, gaps."""
    from kairos.wiki.lint import lint_wiki

    root = (project or resolve_root()).resolve()
    cfg = load_config(root)
    llm = LLMClient.from_env()
    try:
        result = lint_wiki(project_root=root, llm=llm, fix=fix, stale_after_days=cfg.stale_after_days)
    except MCPUnreachable as e:
        console.print(f"[red]llm provider unreachable[/]: {e}")
        raise typer.Exit(3) from e
    except LLMError as e:
        console.print(f"[red]llm error[/]: {e}")
        raise typer.Exit(3) from e

    table = Table(title="lint findings")
    table.add_column("severity")
    table.add_column("kind")
    table.add_column("page")
    table.add_column("provenance")
    table.add_column("note")
    for f in result.findings:
        sev_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(f.severity, "white")
        prov = getattr(f, "provenance", "local")
        prov_label = "[magenta]llm[/]" if prov == "llm" else "[green]local[/]"
        # KAI-007: f.note may contain [[wikilinks]]; render the cell raw via Text.
        from rich.text import Text

        note_cell = Text(f.note[:80])
        table.add_row(
            f"[{sev_color}]{f.severity}[/]",
            f.kind,
            f.page,
            prov_label,
            note_cell,
        )
    console.print(table)
    console.print(f"[dim]report: {result.report_path.relative_to(root)}[/]")


@app.command()
def run(
    task: str = typer.Argument(..., help="The task to solve."),
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
    technique: str = typer.Option("auto", "--technique", "-t", help="rag | react | reflexion | auto"),
    dry: bool = typer.Option(False, "--dry", help="Return top-3 candidate techniques without running."),
    json_out: bool = typer.Option(False, "--json", help="Emit the full trace as JSON instead of a table."),
    llm_rerank: bool = typer.Option(
        False,
        "--llm-rerank",
        help="(KAI-020) When auto-selecting and the top-3 are within 0.05, ask the LLM to break the tie.",
    ),
) -> None:
    """Pick + execute a technique for `task`. Logs the run to .kairos/kairos.db."""
    from kairos.runners import dispatch
    from kairos.selector import select_technique

    root = (project or resolve_root()).resolve()
    cfg = load_config(root)
    llm = LLMClient.from_env()

    selected_by = "user"
    selector_score: float | None = None

    try:
        if technique == "auto":
            ranking = select_technique(
                task=task,
                project_root=root,
                llm=llm,
                require_runner=cfg.require_runner,
                tie_break_threshold=cfg.tie_break_threshold,
                default_technique=cfg.default_technique,
            )
            if dry:
                if json_out:
                    dry_payload: dict[str, object] = {
                        "task": task,
                        "candidates": [
                            {
                                "rank": i,
                                "technique": choice.technique,
                                "score": choice.score,
                                "rationale": choice.rationale,
                            }
                            for i, choice in enumerate(ranking[:3], 1)
                        ],
                    }
                    typer.echo(_json.dumps(dry_payload, sort_keys=True))
                    return
                table = Table(title=f"top-3 techniques for: {task}")
                table.add_column("rank")
                table.add_column("technique")
                table.add_column("score")
                table.add_column("rationale")
                for i, choice in enumerate(ranking[:3], 1):
                    table.add_row(str(i), choice.technique, f"{choice.score:.2f}", choice.rationale)
                console.print(table)
                return
            if llm_rerank and len(ranking) >= 2:
                ranking = _llm_rerank_ranking(task=task, ranking=ranking, llm=llm)
            chosen = ranking[0].technique
            selected_by = "selector"
            selector_score = float(ranking[0].score)
            if not json_out:
                console.print(
                    f"[cyan]selector picked:[/] [bold]{chosen}[/] (score={selector_score:.2f})"
                )
        else:
            chosen = technique

        runner_kwargs: dict[str, object] = {}
        if chosen == "rag":
            runner_kwargs.update({"chunk_size": cfg.rag_chunk_size, "top_k": cfg.rag_top_k})
        elif chosen == "react":
            runner_kwargs["max_steps"] = cfg.max_react_steps

        result = dispatch(
            chosen,
            task=task,
            project_root=root,
            llm=llm,
            selected_by=selected_by,
            selector_score=selector_score,
            **runner_kwargs,
        )
    except MCPUnreachable as e:
        console.print(f"[red]llm provider unreachable[/]: {e}")
        raise typer.Exit(3) from e
    except LLMError as e:
        console.print(f"[red]llm error[/]: {e}")
        raise typer.Exit(3) from e

    if json_out:
        # KAI-034: trace is no longer carried on RunResult; read it back from
        # disk if a trace_path was produced. Best-effort - if the file is
        # missing or malformed we ship an empty list rather than crashing.
        trace_events: list[dict[str, object]] = []
        if result.trace_path and result.trace_path.exists():
            for line in result.trace_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    loaded = _json.loads(line)
                except _json.JSONDecodeError:
                    continue
                if isinstance(loaded, dict):
                    trace_events.append(loaded)

        run_payload: dict[str, object] = {
            "run_id": result.run_id,
            "technique": result.technique,
            "task": result.task,
            "status": result.status,
            "duration_ms": result.duration_ms,
            "selected_by": selected_by,
            "selector_score": selector_score,
            "answer": result.answer,
            "answer_path": str(result.answer_path) if result.answer_path else None,
            "trace_path": str(result.trace_path) if result.trace_path else None,
            "trace": trace_events,
            "error": result.error,
        }
        typer.echo(_json.dumps(run_payload, sort_keys=True))
        return

    console.rule(f"[bold cyan]{chosen}[/] -> answer")
    # KAI-007: LLM reply may contain [[wikilinks]]; do not let Rich eat them.
    console.print(result.answer, markup=False)
    console.rule(f"[dim]run id={result.run_id}, duration={result.duration_ms:.1f}ms[/]")


def _llm_rerank_ranking(
    *,
    task: str,
    ranking: list[TechniqueChoice],
    llm: LLMClient,
) -> list[TechniqueChoice]:
    """KAI-020: optional LLM tie-break for the top-3 candidates.

    Best-effort: on any LLM error we fall back to the original ranking.
    """
    if len(ranking) < 2:
        return ranking
    top = ranking[0].score
    close = [r for r in ranking[:3] if abs(r.score - top) < 0.05]
    if len(close) < 2:
        return ranking
    options = "\n".join(
        f"- {r.technique} (score {r.score:.2f}, rationale: {r.rationale})" for r in close
    )
    prompt = (
        f"You are a tie-break advisor. Pick the BEST technique for this task and "
        f"reply with ONLY the lowercase technique name.\n\n"
        f"TASK: {task}\n\nCANDIDATES:\n{options}\n\n"
        f"Reply with one of: {', '.join(r.technique for r in close)}"
    )
    try:
        reply_text = llm.claude_send(prompt).text.strip().lower()
    except LLMError:
        return ranking
    reply = reply_text.split()[0] if reply_text else ""
    for r in close:
        if r.technique == reply:
            ranking.remove(r)
            ranking.insert(0, r)
            return ranking
    return ranking


@app.command()
def feedback(
    run_id: int = typer.Argument(..., help="Run id from `kairos run` (see .kairos/kairos.db / outputs/run-NNNNN)."),
    rating: int = typer.Option(..., "--rating", "-r", help="Quality rating 1-5 (5 = best)."),
    note: str = typer.Option("", "--note", "-n", help="Optional free-form note."),
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
) -> None:
    """KAI-035: record feedback for a previous run into the feedback table."""
    if rating < 1 or rating > 5:
        console.print("[red]error[/]: --rating must be in 1..5")
        raise typer.Exit(2)

    from kairos.memory.db import Database

    root = (project or resolve_root()).resolve()
    paths = WikiPaths(root=root)
    db = Database(path=paths.db)
    with db.conn() as conn:
        exists = conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
    if exists is None:
        console.print(f"[red]error[/]: run id {run_id} not found")
        raise typer.Exit(1)
    feedback_id = db.insert_feedback(run_id=run_id, rating=rating, note=note or None)
    console.print(
        f"[green]recorded[/]: feedback id={feedback_id} for run {run_id} (rating={rating})"
    )


@app.command()
def history(
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum runs to show."),
) -> None:
    """List recent runs from .kairos/kairos.db."""
    from kairos.memory.db import Database

    root = (project or resolve_root()).resolve()
    rows = Database(path=WikiPaths(root=root).db).list_runs(limit=limit)
    table = Table(title="kairos history")
    for column in ("id", "ts", "technique", "status", "task"):
        table.add_column(column)
    for row in rows:
        table.add_row(
            str(row["id"]),
            str(row["ts"]),
            str(row["technique"]),
            str(row["status"]),
            str(row["task"])[:80],
        )
    console.print(table)


@app.command("feedback-list")
def list_feedback(
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
    run_id: int | None = typer.Option(None, "--run-id", help="Filter feedback for one run id."),
) -> None:
    """List recorded feedback rows."""
    from kairos.memory.db import Database

    root = (project or resolve_root()).resolve()
    rows = Database(path=WikiPaths(root=root).db).list_feedback(run_id=run_id)
    table = Table(title="kairos feedback")
    for column in ("id", "run_id", "rating", "ts", "note"):
        table.add_column(column)
    for row in rows:
        table.add_row(
            str(row["id"]),
            str(row["run_id"]),
            str(row["rating"]),
            str(row["ts"]),
            str(row["note"] or ""),
        )
    console.print(table)


@app.command()
def doctor() -> None:
    """Print environment diagnostics: paths, provider reachability, schema validity."""
    root = resolve_root()
    paths = WikiPaths(root=root)
    cfg = load_config(root)
    table = Table(title="kairos doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")
    table.add_row("project root", "[green]ok[/]" if paths.agents_md.exists() else "[red]missing[/]", str(root))
    table.add_row("AGENTS.md", "[green]ok[/]" if paths.agents_md.exists() else "[red]missing[/]", str(paths.agents_md))
    table.add_row("wiki/", "[green]ok[/]" if paths.wiki.is_dir() else "[red]missing[/]", str(paths.wiki))
    table.add_row(
        ".kairos/config.toml",
        "[green]ok[/]" if cfg.config_file else "[dim]not present (defaults)[/]",
        str(cfg.config_file) if cfg.config_file else "(using built-in defaults)",
    )
    if cfg.config_had_bom:
        table.add_row(
            "config warning",
            "[yellow]warning[/]",
            "config.toml had a UTF-8 BOM; parsed with utf-8-sig",
        )
    # KAI-011/v0.4: real liveness probe instead of a hard-coded 'ok'.
    backend = cfg.llm_backend
    if backend == "mcp":
        status = "[yellow]migration required[/]"
        detail = "llm-mcp backend was removed; use ollama, openai, anthropic, openai_compat, or stub"
    elif backend == "stub":
        status = "[green]ok[/]"
        detail = "stub backend, no network"
    else:
        try:
            client = LLMClient.from_env()
            reachable = client.ping()
        except LLMError as exc:
            reachable = False
            detail = f"{backend} ({exc})"
        else:
            detail = f"{backend} {'live' if reachable else 'no response'}"
        status = "[green]ok[/]" if reachable else "[yellow]unreachable[/]"
    table.add_row("llm backend", status, detail)
    table.add_row("kairos version", "[green]ok[/]", __version__)
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
