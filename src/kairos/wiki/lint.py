"""kairos lint — wiki health check.

Two passes:
  - Local pass (deterministic, runs without network):
      * orphans (no incoming wikilinks AND no outgoing wikilinks)
      * missing concepts referenced but not created
      * frontmatter parse failures
      * stale pages (updated >180 days ago)
      * heavy single sources (one source over-represented)
  - LLM pass (via claude_send): contradictions, claim drift, gaps.

Findings written to outputs/lint-YYYY-MM-DD.md.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Literal

from kairos.llm.mcp_client import LLMClient
from kairos.utils.paths import WikiPaths
from kairos.wiki.schema import (
    PageFrontmatter,
    extract_wikilinks,
    parse_page,
    validate_schema_loaded,
)

Severity = Literal["high", "medium", "low"]


@dataclass
class Finding:
    """One lint finding."""

    severity: Severity
    kind: str
    page: str
    note: str


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
    """Scan wiki/* and produce a lint report."""
    validate_schema_loaded(project_root)
    paths = WikiPaths(root=project_root)

    findings: list[Finding] = []
    pages: dict[str, tuple[Path, PageFrontmatter, str]] = {}
    incoming_links: dict[str, set[str]] = {}
    outgoing_links: dict[str, set[str]] = {}
    pages_scanned = 0

    # Local pass.
    for sub in (paths.concepts, paths.sources, paths.comparisons):
        for path in sub.glob("*.md"):
            pages_scanned += 1
            text = path.read_text(encoding="utf-8")
            slug = path.stem
            try:
                fm, body = parse_page(text)
            except ValueError as e:
                findings.append(
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
            outgoing_links[slug] = outs
            for tgt in outs:
                incoming_links.setdefault(tgt, set()).add(slug)

    # missing-target / orphan / stale
    today = _dt.date.today()
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

    # source over-representation
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
                    note=f"cited by {n} pages — consider diversifying",
                )
            )

    # LLM pass: contradictions / drift / gaps. Skipped if there are no pages.
    if pages:
        excerpts = []
        for _slug, (path, _fm, body) in pages.items():
            excerpts.append(
                dedent(
                    f"""
                    --- {path.relative_to(project_root).as_posix()} ---
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
        findings.extend(_parse_llm_findings(reply))

    # Write report.
    paths.outputs.mkdir(parents=True, exist_ok=True)
    report_path = paths.outputs / f"lint-{today.isoformat()}.md"
    report_path.write_text(_render_report(findings, pages_scanned, today), encoding="utf-8")

    if fix:
        # v0.1: --fix is a no-op placeholder. v0.2 will apply suggested edits.
        pass

    return LintResult(findings=findings, report_path=report_path, pages_scanned=pages_scanned)


def _strip_link(s: str) -> str:
    s = s.strip()
    if s.startswith("[[") and s.endswith("]]"):
        return s[2:-2].strip()
    return s


_FINDING_RE = re.compile(
    r"^[-*]\s*\[(?P<sev>high|medium|low)\]\s*(?P<kind>[\w-]+)\s*\|\s*(?P<page>[^|]+)\s*\|\s*(?P<note>.+)$",
    re.IGNORECASE,
)


def _parse_llm_findings(reply: str) -> list[Finding]:
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
        out.append(Finding(severity=sev, kind=kind, page=page, note=m.group("note").strip()))  # type: ignore[arg-type]
    return out


def _render_report(findings: list[Finding], pages_scanned: int, today: _dt.date) -> str:
    by_severity: dict[str, list[Finding]] = {"high": [], "medium": [], "low": []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)

    lines = [
        f"# kairos lint — {today.isoformat()}",
        "",
        f"Pages scanned: **{pages_scanned}**.",
        f"Findings: {len(findings)} (high {len(by_severity['high'])}, medium {len(by_severity['medium'])}, low {len(by_severity['low'])}).",
        "",
    ]
    for sev in ("high", "medium", "low"):
        items = by_severity.get(sev, [])
        if not items:
            continue
        lines.append(f"## {sev.title()} severity")
        lines.append("")
        for f in items:
            lines.append(f"- **{f.kind}** | `{f.page}` — {f.note}")
        lines.append("")
    if not findings:
        lines.append("No findings. Wiki looks consistent.")
        lines.append("")
    return "\n".join(lines)
