"""kairos lint - wiki health check.

Two passes:
  - Local pass (deterministic, runs without network):
      * orphans (no incoming wikilinks AND no outgoing wikilinks)
      * missing concepts referenced but not created
      * frontmatter parse failures
      * stale pages (updated >180 days ago)
      * heavy single sources (one source over-represented)
  - LLM pass (via claude_send): contradictions, claim drift, gaps.

Findings written to outputs/lint-YYYY-MM-DD.md.

v0.2: KAI-010 adds a `provenance` field on every Finding so the report
visibly separates deterministic results from LLM-generated ones; LLM findings
that name pages we cannot find on disk are dropped entirely.
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Literal

from kairos.llm.mcp_client import LLMClient
from kairos.memory.wiki_index import WikiIndexer, normalize_wikilink
from kairos.utils.paths import WikiPaths
from kairos.wiki.schema import (
    PageFrontmatter,
    extract_wikilinks,
    parse_page,
    validate_schema_loaded,
)

Severity = Literal["high", "medium", "low"]
Provenance = Literal["local", "llm"]


@dataclass
class Finding:
    """One lint finding."""

    severity: Severity
    kind: str
    page: str
    note: str
    provenance: Provenance = "local"


@dataclass
class LintResult:
    """The full lint report."""

    findings: list[Finding] = field(default_factory=list)
    report_path: Path = field(default_factory=lambda: Path("."))
    pages_scanned: int = 0


def lint_wiki(
    *,
    project_root: Path,
    llm: LLMClient,
    fix: bool = False,
    stale_after_days: int = 180,
) -> LintResult:
    """Scan wiki/* and produce a lint report.

    KAI-027: orchestrator only. Heavy lifting lives in the four `_*` helpers
    below so each pass can be reasoned about, tested, and replaced in isolation.
    """
    validate_schema_loaded(project_root)
    paths = WikiPaths(root=project_root)

    pages, outgoing_links, incoming_links, parse_findings = _collect_pages_and_links(
        paths=paths, project_root=project_root
    )
    _refresh_index_from_lint(paths=paths, pages=pages, outgoing_links=outgoing_links)
    today = _dt.date.today()
    local = parse_findings + _local_findings(
        pages=pages,
        outgoing_links=outgoing_links,
        incoming_links=incoming_links,
        project_root=project_root,
        today=today,
        stale_after_days=stale_after_days,
    )
    llm_findings = _llm_findings(pages=pages, paths=paths, llm=llm) if pages else []

    findings = local + llm_findings
    paths.outputs.mkdir(parents=True, exist_ok=True)
    report_path = paths.outputs / f"lint-{today.isoformat()}.md"
    report_path.write_text(
        _render_report(findings, len(pages) + len(parse_findings), today),
        encoding="utf-8",
    )

    if fix:
        # v0.1: --fix is a no-op placeholder. v0.2 will apply suggested edits.
        pass

    return LintResult(
        findings=findings,
        report_path=report_path,
        pages_scanned=len(pages) + len(parse_findings),
    )


def _refresh_index_from_lint(
    *,
    paths: WikiPaths,
    pages: dict[str, tuple[Path, PageFrontmatter, str]],
    outgoing_links: dict[str, set[str]],
) -> None:
    """Mirror lint's parsed pages into wiki_index and prune deleted rows."""
    indexer = WikiIndexer(db_path=paths.db)
    seen: set[str] = set()
    for slug, (path, fm, body) in pages.items():
        seen.add(slug)
        rel = path.relative_to(paths.root).as_posix()
        indexer.upsert_page(slug=slug, fm=fm, body=body, file_rel=rel)
        indexer.upsert_relations(from_slug=slug, links=outgoing_links.get(slug, ()), related=fm.related)
    for row in indexer.all_pages():
        slug = str(row.get("slug", ""))
        file_rel = row.get("file")
        if slug and (slug not in seen or not isinstance(file_rel, str) or not (paths.root / file_rel).exists()):
            indexer.remove_page(slug)


def _collect_pages_and_links(
    *, paths: WikiPaths, project_root: Path
) -> tuple[
    dict[str, tuple[Path, PageFrontmatter, str]],
    dict[str, set[str]],
    dict[str, set[str]],
    list[Finding],
]:
    """KAI-027 helper: walk wiki/, parse pages, build link graph.

    Returns (pages_by_slug, outgoing, incoming, parse_failures).
    """
    pages: dict[str, tuple[Path, PageFrontmatter, str]] = {}
    incoming: dict[str, set[str]] = {}
    outgoing: dict[str, set[str]] = {}
    parse_failures: list[Finding] = []

    for sub in (paths.concepts, paths.sources, paths.comparisons):
        for path in sub.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            slug = path.stem
            try:
                fm, body = parse_page(text)
            except ValueError as e:
                parse_failures.append(
                    Finding(
                        severity="high",
                        kind="parse-error",
                        page=path.relative_to(project_root).as_posix(),
                        note=str(e),
                    )
                )
                continue
            pages[slug] = (path, fm, body)
            outs = set(extract_wikilinks(body) + [_strip_link(s) for s in fm.related])
            outgoing[slug] = outs
            for tgt in outs:
                incoming.setdefault(tgt, set()).add(slug)
    return pages, outgoing, incoming, parse_failures


def _local_findings(
    *,
    pages: dict[str, tuple[Path, PageFrontmatter, str]],
    outgoing_links: dict[str, set[str]],
    incoming_links: dict[str, set[str]],
    project_root: Path,
    today: _dt.date,
    stale_after_days: int,
) -> list[Finding]:
    """KAI-027 helper: deterministic checks (missing/orphan/stale/dominant)."""
    findings: list[Finding] = []
    for slug, (path, fm, _body) in pages.items():
        rel = path.relative_to(project_root).as_posix()
        outs = outgoing_links.get(slug, set())
        for tgt in outs:
            if tgt and tgt not in pages:
                findings.append(
                    Finding(
                        severity="medium",
                        kind="missing-concept",
                        page=rel,
                        note=f"links to [[{tgt}]] but no such page exists",
                    )
                )
        if not incoming_links.get(slug) and not outs and fm.type == "concept":
            findings.append(
                Finding(
                    severity="low",
                    kind="orphan",
                    page=rel,
                    note="concept page has no incoming or outgoing wikilinks",
                )
            )
        if isinstance(fm.updated, _dt.date):
            age = (today - fm.updated).days
            if age > stale_after_days:
                findings.append(
                    Finding(
                        severity="low",
                        kind="stale",
                        page=rel,
                        note=f"updated {age} days ago (threshold {stale_after_days})",
                    )
                )

    src_counts: dict[str, int] = {}
    for _slug, (_path, fm, _body) in pages.items():
        for s in fm.sources:
            src_counts[s] = src_counts.get(s, 0) + 1
    for src, n in src_counts.items():
        if n >= 8:
            findings.append(
                Finding(
                    severity="low",
                    kind="dominant-source",
                    page=src,
                    note=f"cited by {n} pages - consider diversifying",
                )
            )
    return findings


def _llm_findings(
    *,
    pages: dict[str, tuple[Path, PageFrontmatter, str]],
    paths: WikiPaths,
    llm: LLMClient,
) -> list[Finding]:
    """KAI-027 helper: ask the LLM for contradiction/drift findings.

    Filters out findings that name pages we cannot find on disk (KAI-010).
    """
    excerpts = []
    for _slug, (path, _fm, body) in pages.items():
        excerpts.append(
            dedent(
                f"""
                --- {path.relative_to(paths.root).as_posix()} ---
                {body[:1200]}
                """
            ).strip()
        )
    joined = "\n\n".join(excerpts)[:14000]
    schema_text = paths.agents_md.read_text(encoding="utf-8")
    prompt = dedent(
        f"""
        You are linting a wiki for contradictions, claim drift, and gaps.
        Schema attached. Be concise and concrete: every finding must name
        the page(s) involved and 1 sentence of evidence.

        SCHEMA (AGENTS.md):
        ---
        {schema_text}
        ---

        WIKI EXCERPTS:
        ---
        {joined}
        ---

        Return findings as a markdown bulleted list, one per line, format:
        - [SEVERITY] kind | page-or-pages | one-sentence note

        SEVERITY in {{high, medium, low}}. kind in {{contradiction, drift,
        gap, ambiguity}}. If nothing wrong, return: "- [low] no findings | - | wiki looks consistent".
        Keep total response under 300 words.
        """
    ).strip()
    reply = llm.claude_send(prompt).text
    return _parse_llm_findings(reply, known_pages=set(pages))


def _strip_link(s: str) -> str:
    return normalize_wikilink(s)


_FINDING_RE = re.compile(
    r"^[-*]\s*\[(?P<sev>high|medium|low)\]\s*(?P<kind>[\w-]+(?:\s+[\w-]+)*)\s*\|\s*(?P<page>[^|]+)\s*\|\s*(?P<note>.+)$",
    re.IGNORECASE,
)


def _parse_llm_findings(reply: str, *, known_pages: set[str]) -> list[Finding]:
    """KAI-010: LLM findings are tagged provenance='llm' and dropped when they
    name a page that doesn't exist on disk (likely hallucinated)."""
    out: list[Finding] = []
    for line in reply.splitlines():
        m = _FINDING_RE.match(line.strip())
        if not m:
            continue
        sev = m.group("sev").lower()
        kind = m.group("kind").strip().lower()
        if sev not in {"high", "medium", "low"}:
            continue
        page = m.group("page").strip()
        if page.startswith("-"):
            page = "(wiki)"
        # If the LLM names specific page paths, every named slug must exist.
        # Page strings can be comma-separated lists (the LLM's contract per
        # the prompt: "page-or-pages").
        slugs = [
            Path(p.strip()).stem
            for p in re.split(r",\s*", page)
            if p.strip() and p.strip() != "(wiki)"
        ]
        if slugs and not all(s in known_pages for s in slugs):
            print(
                f"[lint] dropping LLM finding for unknown page(s): {page}",
                file=sys.stderr,
            )
            continue
        out.append(
            Finding(
                severity=sev,  # type: ignore[arg-type]
                kind=kind,
                page=page,
                note=m.group("note").strip(),
                provenance="llm",
            )
        )
    return out


def _render_report(findings: list[Finding], pages_scanned: int, today: _dt.date) -> str:
    """KAI-010: render local findings and LLM findings in separate sections."""
    local = [f for f in findings if getattr(f, "provenance", "local") == "local"]
    llm = [f for f in findings if getattr(f, "provenance", "local") == "llm"]

    lines = [
        f"# kairos lint - {today.isoformat()}",
        "",
        f"Pages scanned: **{pages_scanned}**.",
        f"Findings: {len(findings)} (deterministic {len(local)}, llm {len(llm)}).",
        "",
    ]
    if local:
        lines.append("## Deterministic findings")
        lines.append("")
        lines.extend(_format_findings_section(local))
    if llm:
        lines.append("## LLM-generated findings (verify manually)")
        lines.append("")
        lines.append(
            "_LLM findings are advisory. Each was filtered to reference an existing wiki page,_"
        )
        lines.append("_but you should still confirm before acting._")
        lines.append("")
        lines.extend(_format_findings_section(llm))
    if not findings:
        lines.append("No findings. Wiki looks consistent.")
        lines.append("")
    return "\n".join(lines)


def _format_findings_section(findings: list[Finding]) -> list[str]:
    by_severity: dict[str, list[Finding]] = {"high": [], "medium": [], "low": []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)
    out: list[str] = []
    for sev in ("high", "medium", "low"):
        items = by_severity.get(sev, [])
        if not items:
            continue
        out.append(f"### {sev.title()} severity")
        out.append("")
        for f in items:
            out.append(f"- **{f.kind}** | `{f.page}` - {f.note}")
        out.append("")
    return out
