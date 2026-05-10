"""kairos query "<question>" — answer questions over the wiki.

Workflow per AGENTS.md:
  1. Read wiki/index.md.
  2. Identify candidate concept and source pages.
  3. Read those pages.
  4. Synthesize an answer with [[wikilinks]].
  5. Optionally save the answer back as a new wiki page.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

from kairos.llm.mcp_client import LLMClient
from kairos.utils.paths import WikiPaths
from kairos.wiki.schema import (
    PageFrontmatter,
    extract_wikilinks,
    parse_page,
    render_page,
    validate_schema_loaded,
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]+")
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "is", "to", "for", "in", "on",
        "what", "how", "why", "when", "where", "do", "does", "did", "which",
        "should", "would", "could", "with", "from", "by", "be", "are", "this",
    }
)


@dataclass
class QueryResult:
    """Output of `kairos query`."""

    question: str
    answer: str
    pages_read: list[Path] = field(default_factory=list)
    saved_to: Path | None = None


def query_wiki(
    question: str,
    *,
    project_root: Path,
    llm: LLMClient,
    save_to_wiki: bool = False,
    max_pages: int = 8,
) -> QueryResult:
    """Answer a question grounded in the wiki."""
    validate_schema_loaded(project_root)
    paths = WikiPaths(root=project_root)

    # 1. Pick candidate pages by simple lexical overlap on titles + body keywords.
    candidates = _rank_candidate_pages(paths, question, top_k=max_pages)
    pages_read: list[Path] = []
    excerpts: list[str] = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
            fm, body = parse_page(text)
        except Exception:  # noqa: BLE001
            continue
        pages_read.append(path)
        excerpts.append(
            dedent(
                f"""
                ---
                page: {path.relative_to(project_root).as_posix()}
                title: {fm.title}
                type: {fm.type}
                confidence: {fm.confidence}
                ---
                {body[:2000]}
                """
            ).strip()
        )

    schema = paths.agents_md.read_text(encoding="utf-8")
    index_md = paths.index_md.read_text(encoding="utf-8") if paths.index_md.exists() else ""

    prompt = dedent(
        f"""
        You are answering a question grounded in this wiki. Follow the schema
        rules. Cite using [[wikilinks]] (slug only). Refuse to fabricate.

        SCHEMA (AGENTS.md):
        ---
        {schema}
        ---

        WIKI INDEX:
        ---
        {index_md[:4000]}
        ---

        RELEVANT PAGES (top {len(excerpts)} by lexical overlap):
        ---
        {chr(10).join(excerpts) or "(no relevant pages found)"}
        ---

        QUESTION: {question}

        Answer in markdown. Begin with one paragraph, then a bulleted "Sources"
        section listing the [[wikilinks]] of pages you cited. If the wiki does
        not contain enough information, say so explicitly and suggest what to
        ingest.
        """
    ).strip()

    answer = llm.claude_send(prompt).text.strip() or "(no answer)"

    # 2. Append a query event to the log.
    log_line = f"## [{_dt.date.today().isoformat()}] query | {question}\n- pages read: {len(pages_read)}\n\n"
    with paths.log_md.open("a", encoding="utf-8") as f:
        f.write(log_line)

    # 3. Optional: save answer back as a new wiki page (Karpathy's "answers compound").
    saved_to: Path | None = None
    if save_to_wiki:
        from kairos.wiki.ingest import slugify

        today = _dt.date.today()
        slug = slugify(question)[:60]
        page_path = paths.concepts / f"q-{slug}.md"
        fm = PageFrontmatter(
            title=question,
            type="concept",
            sources=[],
            related=extract_wikilinks(answer),
            created=today,
            updated=today,
            confidence="medium",
        )
        page_path.write_text(render_page(fm, answer + "\n"), encoding="utf-8")
        saved_to = page_path

    return QueryResult(
        question=question,
        answer=answer,
        pages_read=pages_read,
        saved_to=saved_to,
    )


def _rank_candidate_pages(paths: WikiPaths, question: str, *, top_k: int) -> list[Path]:
    """Rank wiki pages by token overlap with the question; return top_k paths."""
    q_tokens = {t for t in _WORD_RE.findall(question.lower()) if t not in _STOPWORDS}
    if not q_tokens:
        # fall back: return up to top_k arbitrary concept pages
        return sorted(paths.concepts.glob("*.md"))[:top_k]

    scored: list[tuple[float, Path]] = []
    for sub in (paths.concepts, paths.sources, paths.comparisons):
        for path in sub.glob("*.md"):
            try:
                text = path.read_text(encoding="utf-8").lower()
            except OSError:
                continue
            tokens = set(_WORD_RE.findall(text)) - _STOPWORDS
            score = len(q_tokens & tokens)
            slug_match = sum(1 for t in q_tokens if t in path.stem)
            scored.append((score + 2.0 * slug_match, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored[:top_k] if s > 0]
