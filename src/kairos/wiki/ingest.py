"""kairos ingest <file> - drop a source into raw/ and let the LLM file it.

Karpathy ingest workflow:
  1. Read the source.
  2. Discuss takeaways briefly.
  3. Create wiki/sources/<slug>.md.
  4. Update or create concept pages.
  5. Update wiki/index.md.
  6. Append wiki/log.md.

In v0.1 we keep this surgical: one llm-mcp call per source, the LLM is asked
to return a strict JSON envelope describing what to write. We then write the
files locally in Python. This keeps the LLM stateless and the file writes
auditable.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any

from kairos.llm.mcp_client import LLMClient
from kairos.memory.wiki_index import WikiIndexer
from kairos.utils.paths import WikiPaths
from kairos.wiki.schema import (
    PageFrontmatter,
    extract_wikilinks,
    parse_page,
    render_page,
    validate_schema_loaded,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class IngestResult:
    """What ingest produced. Useful for the CLI report and tests."""

    raw_path: Path
    source_page: Path
    concept_pages_updated: list[Path] = field(default_factory=list)
    concept_pages_created: list[Path] = field(default_factory=list)
    log_entry: str = ""
    title: str = ""

    @property
    def all_writes(self) -> list[Path]:
        return [
            self.source_page,
            *self.concept_pages_created,
            *self.concept_pages_updated,
        ]


def slugify(s: str) -> str:
    """Filesystem-safe kebab-case slug."""
    base = _SLUG_RE.sub("-", s.lower()).strip("-")
    return base or "untitled"


def ingest_file(
    source_file: Path,
    *,
    project_root: Path,
    llm: LLMClient,
    max_concept_updates: int = 15,
) -> IngestResult:
    """Ingest a single file into the project's wiki.

    Args:
        source_file: path to the file the user wants ingested. Need not be inside raw/ yet.
        project_root: directory containing AGENTS.md and wiki/.
        llm: an LLMClient (stub or real).
        max_concept_updates: cap on cascading wiki edits per ingest.
    """
    validate_schema_loaded(project_root)
    paths = WikiPaths(root=project_root)
    paths.ensure_dirs()

    source_text = source_file.read_text(encoding="utf-8", errors="replace")
    title = _extract_title(source_text, fallback=source_file.stem)
    slug = slugify(title)

    # Move/copy the source into raw/articles unless it's already inside raw/.
    # KAI-002: when an existing raw copy with the same name is byte-different
    # from the new source, we write to a numeric-suffixed sibling so the
    # corpus reflects the latest content (no silent stale copies).
    raw_target = source_file.resolve()
    try:
        raw_target.relative_to(paths.raw.resolve())
    except ValueError:
        candidate = paths.raw / "articles" / source_file.name
        candidate.parent.mkdir(parents=True, exist_ok=True)
        raw_target = _resolve_raw_target(candidate, source_file)

    raw_rel = raw_target.relative_to(project_root.resolve()).as_posix()

    # Existing concept pages we might link to.
    existing_concepts = sorted(
        p.stem for p in paths.concepts.glob("*.md") if p.is_file()
    )

    schema_text = paths.agents_md.read_text(encoding="utf-8")
    prompt = _build_prompt(
        schema_text=schema_text,
        source_text=source_text,
        raw_rel=raw_rel,
        title=title,
        slug=slug,
        existing_concepts=existing_concepts,
        max_concept_updates=max_concept_updates,
    )

    reply = llm.claude_send(prompt).text
    plan = _parse_plan_json(reply, fallback_title=title)

    today = _dt.date.today()

    # 1. Write the source summary page.
    # KAI-003: if a different source already owns this slug (different raw_rel),
    # bump to slug-2.md (counter) so we never silently clobber a peer.
    # KAI-024: preserve `created` from the prior page if this slug has been
    # ingested before by the SAME raw_rel.
    source_path, original_created = _resolve_source_page_path(
        sources_dir=paths.sources, slug=slug, raw_rel=raw_rel
    )
    src_fm = PageFrontmatter(
        title=plan["source_page"]["title"],
        type="source",
        sources=[raw_rel],
        related=plan["source_page"].get("related", []),
        created=original_created or today,
        updated=today,
        confidence=plan["source_page"].get("confidence", "medium"),
    )
    source_path.write_text(
        render_page(src_fm, plan["source_page"]["body"]),
        encoding="utf-8",
    )

    # 2. Apply concept-page updates (capped).
    updated: list[Path] = []
    created: list[Path] = []
    for entry in plan.get("concept_updates", [])[:max_concept_updates]:
        target_slug = slugify(entry["slug"])
        target = paths.concepts / f"{target_slug}.md"
        new_body = entry.get("body") or ""
        new_title = entry.get("title", target_slug.replace("-", " ").title())
        confidence = entry.get("confidence", "medium")
        related = entry.get("related", [])
        sources = list(set([raw_rel, *entry.get("sources", [])]))
        action = entry.get("action", "create" if not target.exists() else "update")

        if action == "update" and target.exists():
            existing_fm, existing_body = parse_page(target.read_text(encoding="utf-8"))
            existing_fm.updated = today
            existing_fm.sources = sorted(set([*existing_fm.sources, *sources]))
            existing_fm.related = sorted(set([*existing_fm.related, *related]))
            merged_body = (existing_body.rstrip() + "\n\n" + new_body.strip() + "\n") if new_body.strip() else existing_body
            target.write_text(render_page(existing_fm, merged_body), encoding="utf-8")
            updated.append(target)
        else:
            fm = PageFrontmatter(
                title=new_title,
                type="concept",
                sources=sources,
                related=related,
                created=today,
                updated=today,
                confidence=confidence,
                has_runner=bool(entry.get("has_runner", False)),
            )
            target.write_text(render_page(fm, new_body), encoding="utf-8")
            created.append(target)

    # 3. Refresh wiki/index.md (coarse rebuild from disk).
    _rebuild_index(paths)

    # 3b. KAI-005: keep the wiki_index/wiki_relations SQLite cache in sync.
    _refresh_wiki_index(paths, source_path=source_path, src_fm=src_fm,
                       src_body=plan["source_page"]["body"], src_slug=source_path.stem,
                       touched_concepts=created + updated)

    # 4. Append wiki/log.md.
    log_entry = f"## [{today.isoformat()}] ingest | {title}\n- source: `{raw_rel}`\n"
    if created:
        log_entry += f"- created concept pages: {', '.join(p.stem for p in created)}\n"
    if updated:
        log_entry += f"- updated concept pages: {', '.join(p.stem for p in updated)}\n"
    log_entry += "\n"
    with paths.log_md.open("a", encoding="utf-8") as f:
        f.write(log_entry)

    return IngestResult(
        raw_path=raw_target,
        source_page=source_path,
        concept_pages_updated=updated,
        concept_pages_created=created,
        log_entry=log_entry.strip(),
        title=title,
    )


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_raw_target(candidate: Path, source_file: Path) -> Path:
    """Pick a raw/ destination for `source_file`, copying when needed (KAI-002).

    - If candidate does not exist: copy and use it.
    - If candidate exists with identical bytes: reuse without copy.
    - If candidate exists with different bytes: walk numeric suffixes
      (`name_2.md`, `name_3.md`, ...) until we find a matching/empty slot.
    """
    if not candidate.exists():
        shutil.copy2(source_file, candidate)
        return candidate
    src_hash = _hash_file(source_file)
    if _hash_file(candidate) == src_hash:
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        alt = candidate.with_name(f"{stem}_{counter}{suffix}")
        if not alt.exists():
            shutil.copy2(source_file, alt)
            return alt
        if _hash_file(alt) == src_hash:
            return alt
        counter += 1


def _resolve_source_page_path(
    *, sources_dir: Path, slug: str, raw_rel: str
) -> tuple[Path, _dt.date | None]:
    """Pick a wiki/sources/<slug>.md path that won't clobber a peer (KAI-003).

    Returns the path and (when re-ingesting the same raw_rel) the original
    `created` date so we can preserve it (KAI-024).
    """
    candidate = sources_dir / f"{slug}.md"
    counter = 1
    while candidate.exists():
        try:
            fm, _ = parse_page(candidate.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            break
        if raw_rel in fm.sources:
            return candidate, fm.created
        counter += 1
        candidate = sources_dir / f"{slug}-{counter}.md"
    return candidate, None


def _refresh_wiki_index(
    paths: WikiPaths,
    *,
    source_path: Path,
    src_fm: PageFrontmatter,
    src_body: str,
    src_slug: str,
    touched_concepts: list[Path],
) -> None:
    """Mirror page metadata + wikilinks into the wiki_index/wiki_relations tables."""
    indexer = WikiIndexer(db_path=paths.db)
    src_rel = source_path.relative_to(paths.root).as_posix()
    indexer.upsert_page(slug=src_slug, fm=src_fm, body=src_body, file_rel=src_rel)
    indexer.upsert_relations(
        from_slug=src_slug,
        links=extract_wikilinks(src_body),
        related=src_fm.related,
    )
    for concept_path in touched_concepts:
        try:
            fm, body = parse_page(concept_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        rel = concept_path.relative_to(paths.root).as_posix()
        slug = concept_path.stem
        indexer.upsert_page(slug=slug, fm=fm, body=body, file_rel=rel)
        indexer.upsert_relations(
            from_slug=slug,
            links=extract_wikilinks(body),
            related=fm.related,
        )


def _build_prompt(
    *,
    schema_text: str,
    source_text: str,
    raw_rel: str,
    title: str,
    slug: str,
    existing_concepts: list[str],
    max_concept_updates: int,
) -> str:
    truncated_source = source_text if len(source_text) <= 12000 else source_text[:12000] + "\n... (truncated)"
    existing = ", ".join(existing_concepts) if existing_concepts else "(none yet)"
    return dedent(
        f"""
        You are the wiki maintainer for a kairos project. Read the schema and the
        source below, then return ONE JSON object describing the writes.

        Hard rules: respect the schema, do NOT modify raw/, surgical changes only,
        confidence honestly, no fabrication, banned phrases listed in schema.

        Existing concept pages already in this wiki: {existing}

        Return JSON ONLY (no prose, no fences) shaped exactly like this:
        {{
          "source_page": {{
            "title": "<short title for this source>",
            "body": "<markdown body, follows the source-page section template in schema>",
            "related": ["[[concept-slug]]", ...],
            "confidence": "high|medium|low"
          }},
          "concept_updates": [
            {{
              "slug": "<kebab-case>",
              "title": "<Title>",
              "action": "create|update",
              "body": "<markdown body. For 'update' this is the delta to APPEND to the existing page.>",
              "related": ["[[other-concept]]"],
              "sources": ["{raw_rel}"],
              "confidence": "high|medium|low",
              "has_runner": false
            }}
          ]
        }}

        Cap concept_updates at {max_concept_updates} entries. Prefer updating
        existing concept pages over creating new ones unless the source genuinely
        introduces a new technique.

        SCHEMA (AGENTS.md):
        ---
        {schema_text}
        ---

        SOURCE (`{raw_rel}`, title: "{title}"):
        ---
        {truncated_source}
        ---
        """
    ).strip()


def _parse_plan_json(
    reply: str,
    *,
    fallback_title: str,
) -> dict[str, Any]:
    """Extract a JSON object from the LLM reply, falling back to a minimal stub."""
    cleaned = reply.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {
        "source_page": {
            "title": fallback_title,
            "body": (
                "## TL;DR\n\n_(ingested but the LLM did not return a parseable plan.)_\n\n"
                "## Key claims\n\n_(to be filled)_\n\n"
                "## Quotes worth keeping\n\n_(to be filled)_\n\n"
                "## Open questions\n\n_(to be filled)_\n"
            ),
            "related": [],
            "confidence": "low",
        },
        "concept_updates": [],
    }


def _extract_title(text: str, *, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 2:
            return stripped[2:].strip()
    return fallback


def _rebuild_index(paths: WikiPaths) -> None:
    """Rebuild wiki/index.md by listing every page on disk grouped by type."""
    sections: dict[str, list[tuple[str, str]]] = {
        "concept": [],
        "source": [],
        "comparison": [],
    }
    for sub, kind in (
        (paths.concepts, "concept"),
        (paths.sources, "source"),
        (paths.comparisons, "comparison"),
    ):
        for f in sorted(sub.glob("*.md")):
            try:
                fm, _ = parse_page(f.read_text(encoding="utf-8"))
                sections[kind].append((fm.title, f.relative_to(paths.root).as_posix()))
            except Exception:  # noqa: BLE001
                # malformed page; lint will surface it later
                sections[kind].append((f.stem, f.relative_to(paths.root).as_posix()))

    lines = ["# Wiki Index", ""]
    lines.append("Master content catalog. Auto-rebuilt on every ingest, lint, query.")
    lines.append("")
    for kind, label in (
        ("concept", "Concepts (agent techniques)"),
        ("source", "Sources"),
        ("comparison", "Comparisons"),
    ):
        lines.append(f"## {label}")
        lines.append("")
        if not sections[kind]:
            lines.append("_(none yet)_")
        else:
            for title, rel in sections[kind]:
                lines.append(f"- [{title}]({rel})")
        lines.append("")
    paths.index_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
