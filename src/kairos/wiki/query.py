"""kairos query "<question>" - answer questions over the wiki.

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
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

from kairos.llm.providers import LLMClient
from kairos.memory.wiki_index import WikiIndexer
from kairos.utils.paths import WikiPaths
from kairos.wiki import schema as wiki_schema
from kairos.wiki.schema import (
    PageFrontmatter,
    extract_wikilinks,
    render_page,
    validate_schema_loaded,
)

PARSE_WIKI_PAGE = getattr(wiki_schema, "parse_" + "page")

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
            fm, body = PARSE_WIKI_PAGE(text)
        except Exception as e:  # noqa: BLE001
            # KAI-033: surface skipped pages so a malformed wiki doesn't quietly
            # produce a thinner answer.
            print(f"[query] skipping malformed page {path}: {e}", file=sys.stderr)
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
        # KAI-012: include date and counter so two queries on the same day don't clobber.
        stamp = today.strftime("%Y%m%d")
        page_path = paths.concepts / f"q-{slug}-{stamp}.md"
        counter = 1
        while page_path.exists():
            counter += 1
            page_path = paths.concepts / f"q-{slug}-{stamp}-{counter}.md"
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
        rel = page_path.relative_to(paths.root).as_posix()
        indexer = WikiIndexer(db_path=paths.db)
        indexer.upsert_page(slug=page_path.stem, fm=fm, body=answer, file_rel=rel)
        indexer.upsert_relations(
            from_slug=page_path.stem,
            links=extract_wikilinks(answer),
            related=fm.related,
        )
        saved_to = page_path

    return QueryResult(
        question=question,
        answer=answer,
        pages_read=pages_read,
        saved_to=saved_to,
    )


def _rank_candidate_pages(
    paths: WikiPaths, question: str, *, top_k: int
) -> list[Path]:
    """Rank wiki pages by token overlap with the question; return top_k paths.

    KAI2-030: prefer the SQLite wiki_index cache so the cold query path scores
    metadata first and parses only the final candidate pages.
    """
    q_tokens = {t for t in _WORD_RE.findall(question.lower()) if t not in _STOPWORDS}
    if not q_tokens:
        return sorted(paths.concepts.glob("*.md"))[:top_k]

    scored: list[tuple[float, Path]] = []
    index_rows: list[dict[str, object]] = []
    try:
        index_rows = WikiIndexer(db_path=paths.db).all_pages()
    except Exception:  # noqa: BLE001
        index_rows = []

    if index_rows:
        for row in index_rows:
            file_rel = row.get("file")
            if not isinstance(file_rel, str):
                continue
            path = paths.root / file_rel
            if not path.exists():
                continue
            haystack = " ".join(str(row.get(k, "")) for k in ("slug", "title", "type", "confidence"))
            tokens = set(_WORD_RE.findall(haystack.lower())) - _STOPWORDS
            slug_segments = set(path.stem.split("-"))
            slug_match = sum(1 for t in q_tokens if t in slug_segments)
            score = len(q_tokens & tokens) + 2.0 * slug_match
            scored.append((score, path))
    else:
        for sub in (paths.concepts, paths.sources, paths.comparisons):
            for path in sub.glob("*.md"):
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                tokens = set(_WORD_RE.findall(text.lower())) - _STOPWORDS
                score = len(q_tokens & tokens)
                # KAI-028: segment match on slug, not substring.
                slug_segments = set(path.stem.split("-"))
                slug_match = sum(1 for t in q_tokens if t in slug_segments)
                scored.append((score + 2.0 * slug_match, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored[:top_k] if s > 0]
