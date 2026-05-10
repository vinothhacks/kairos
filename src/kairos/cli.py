"""kairos CLI — Typer entry point.

Subcommands:
    init    bootstrap a new kairos project
    ingest  ingest a source file into the wiki
    query   ask a question against the wiki
    lint    health-check the wiki
    run     pick + execute a technique for a task
    doctor  print env diagnostics
    version print the package version

Every command is a thin wrapper over a function in src/kairos/wiki/ or
src/kairos/runners/. The CLI does Rich formatting and error handling only.
"""
from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kairos import __version__
from kairos.llm.mcp_client import LLMClient, MCPUnreachable
from kairos.utils.paths import WikiPaths, resolve_root
from kairos.wiki.init import init_project

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="kairos — Stop guessing. Run the right pattern. A CLI for executable agent knowledge.",
)
console = Console()


@app.command()
def version() -> None:
    """Print the kairos version."""
    console.print(f"kairos [bold cyan]{__version__}[/]")


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
        console.print(f"[red]llm-mcp unreachable[/]: {e}")
        raise typer.Exit(3) from e

    console.print(f"[green]ingested[/]: {result.title}")
    table = Table(title=f"writes ({len(result.all_writes)})")
    table.add_column("kind")
    table.add_column("path")
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
    llm = LLMClient.from_env()
    try:
        result = query_wiki(question, project_root=root, llm=llm, save_to_wiki=save)
    except MCPUnreachable as e:
        console.print(f"[red]llm-mcp unreachable[/]: {e}")
        raise typer.Exit(3) from e

    console.rule(f"[bold cyan]Q[/]: {question}")
    console.print(result.answer)
    console.rule(f"[dim]read {len(result.pages_read)} page(s)[/]")
    if result.saved_to:
        console.print(f"[green]saved to wiki[/]: {result.saved_to.relative_to(root)}")


@app.command()
def lint(
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
    fix: bool = typer.Option(False, "--fix", help="(v0.2) Apply suggested edits."),
) -> None:
    """Health-check the wiki: contradictions, orphans, stale claims, gaps."""
    from kairos.wiki.lint import lint_wiki

    root = (project or resolve_root()).resolve()
    llm = LLMClient.from_env()
    try:
        result = lint_wiki(project_root=root, llm=llm, fix=fix)
    except MCPUnreachable as e:
        console.print(f"[red]llm-mcp unreachable[/]: {e}")
        raise typer.Exit(3) from e

    table = Table(title="lint findings")
    table.add_column("severity")
    table.add_column("kind")
    table.add_column("page")
    table.add_column("note")
    for f in result.findings:
        sev_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(f.severity, "white")
        table.add_row(
            f"[{sev_color}]{f.severity}[/]",
            f.kind,
            f.page,
            f.note[:80],
        )
    console.print(table)
    console.print(f"[dim]report: {result.report_path.relative_to(root)}[/]")


@app.command()
def run(
    task: str = typer.Argument(..., help="The task to solve."),
    project: Path = typer.Option(None, "--project", "-p", help="Project root."),
    technique: str = typer.Option("auto", "--technique", "-t", help="rag | react | reflexion | auto"),
    dry: bool = typer.Option(False, "--dry", help="Return top-3 candidate techniques without running."),
) -> None:
    """Pick + execute a technique for `task`. Logs the run to .kairos/kairos.db."""
    from kairos.runners import dispatch
    from kairos.selector import select_technique

    root = (project or resolve_root()).resolve()
    llm = LLMClient.from_env()

    try:
        if technique == "auto":
            ranking = select_technique(task=task, project_root=root, llm=llm)
            if dry:
                table = Table(title=f"top-3 techniques for: {task}")
                table.add_column("rank")
                table.add_column("technique")
                table.add_column("score")
                table.add_column("rationale")
                for i, choice in enumerate(ranking[:3], 1):
                    table.add_row(str(i), choice.technique, f"{choice.score:.2f}", choice.rationale)
                console.print(table)
                return
            chosen = ranking[0].technique
            console.print(f"[cyan]selector picked:[/] [bold]{chosen}[/] (score={ranking[0].score:.2f})")
        else:
            chosen = technique

        result = dispatch(chosen, task=task, project_root=root, llm=llm)
    except MCPUnreachable as e:
        console.print(f"[red]llm-mcp unreachable[/]: {e}")
        raise typer.Exit(3) from e

    console.rule(f"[bold cyan]{chosen}[/] -> answer")
    console.print(result.answer)
    console.rule(f"[dim]run id={result.run_id}, duration={result.duration_ms}ms[/]")


@app.command()
def doctor() -> None:
    """Print environment diagnostics: paths, llm-mcp reachability, schema validity."""
    root = resolve_root()
    paths = WikiPaths(root=root)
    table = Table(title="kairos doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")
    table.add_row("project root", "[green]ok[/]" if paths.agents_md.exists() else "[red]missing[/]", str(root))
    table.add_row("AGENTS.md", "[green]ok[/]" if paths.agents_md.exists() else "[red]missing[/]", str(paths.agents_md))
    table.add_row("wiki/", "[green]ok[/]" if paths.wiki.is_dir() else "[red]missing[/]", str(paths.wiki))
    backend = os.environ.get("KAIROS_LLM_BACKEND", "mcp")
    mcp_url = os.environ.get("KAIROS_MCP_URL", "http://localhost:8765")
    table.add_row("llm backend", "[green]ok[/]", f"{backend} ({mcp_url})")
    table.add_row("kairos version", "[green]ok[/]", __version__)
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
