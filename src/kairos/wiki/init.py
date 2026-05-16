"""kairos init - bootstrap a new kairos project.

Creates the on-disk layout described in AGENTS.md, copies the seed AGENTS.md
and a starter wiki/index.md, and creates an empty wiki/log.md.

The seed wiki (~20 concept pages) lives in `src/kairos/_seed/`. We copy it to
the user's `wiki/concepts/` only if the target is empty.

When `force=True` the previous contents of AGENTS.md / wiki/index.md /
wiki/log.md are written to a timestamped `.bak.<UTC-stamp>` file before being
overwritten, so user content is never silently lost (KAI-001).
"""
from __future__ import annotations

import datetime as _dt
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from kairos.memory.wiki_index import WikiIndexer
from kairos.utils.paths import WikiPaths, seed_dir
from kairos.wiki.schema import extract_wikilinks, parse_page

INDEX_TEMPLATE = """\
# Wiki Index

Master content catalog. Update on every ingest, lint, and query that creates a
new wiki page.

## Concepts (agent techniques)

_(no concept pages yet - `kairos init` will copy the seed wiki here on first run)_

## Sources

_(no sources yet - `kairos ingest <file>` adds them)_

## Comparisons

_(no comparison pages yet)_
"""

LOG_TEMPLATE = """\
# Wiki Log

Append-only chronological log. Format: `## [YYYY-MM-DD] <op> | <subject>`.

"""


@dataclass
class InitResult:
    """What `init_project` did, used for CLI reporting and tests."""

    created: list[Path]
    skipped: list[Path]
    seeded_concepts: int
    backups: list[Path] = field(default_factory=list)

    @property
    def all_paths(self) -> list[Path]:
        return [*self.created, *self.skipped]


def _backup_then_overwrite(target: Path, *, backups: list[Path]) -> None:
    """Move existing `target` to a timestamped `.bak` sibling before overwrite.

    No-op when `target` does not exist. The caller writes the new content after.
    """
    if not target.exists():
        return
    stamp = _dt.datetime.now(tz=_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    bak = target.with_name(target.name + f".bak.{stamp}")
    counter = 1
    while bak.exists():
        counter += 1
        bak = target.with_name(target.name + f".bak.{stamp}-{counter}")
    shutil.copy2(target, bak)
    backups.append(bak)


def init_project(root: Path, *, force: bool = False, with_seed: bool = True) -> InitResult:
    """Create a fresh kairos project at `root`.

    Args:
        root: project directory (created if needed).
        force: if True, overwrite AGENTS.md, index.md, and log.md if they exist.
        with_seed: if True, copy the bundled seed concept pages into wiki/concepts/.

    Returns:
        InitResult listing files created / skipped and the count of seeded concept pages.
    """
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    paths = WikiPaths(root=root)
    paths.ensure_dirs()

    created: list[Path] = []
    skipped: list[Path] = []
    backups: list[Path] = []

    # AGENTS.md schema
    agents_target = paths.agents_md
    seed_agents = seed_dir() / "AGENTS.md"
    if seed_agents.exists():
        if force or not agents_target.exists():
            if force:
                _backup_then_overwrite(agents_target, backups=backups)
            shutil.copy2(seed_agents, agents_target)
            created.append(agents_target)
        else:
            skipped.append(agents_target)
    else:
        # fallback: write a stub if the seed isn't present (dev mode)
        if force or not agents_target.exists():
            if force:
                _backup_then_overwrite(agents_target, backups=backups)
            agents_target.write_text(_minimal_agents_stub(), encoding="utf-8")
            created.append(agents_target)
        else:
            skipped.append(agents_target)

    # wiki/index.md
    if force or not paths.index_md.exists():
        if force:
            _backup_then_overwrite(paths.index_md, backups=backups)
        paths.index_md.write_text(INDEX_TEMPLATE, encoding="utf-8")
        created.append(paths.index_md)
    else:
        skipped.append(paths.index_md)

    # wiki/log.md
    if force or not paths.log_md.exists():
        if force:
            _backup_then_overwrite(paths.log_md, backups=backups)
        today = _dt.date.today().isoformat()
        paths.log_md.write_text(
            LOG_TEMPLATE + f"## [{today}] init | wiki bootstrapped by kairos init\n",
            encoding="utf-8",
        )
        created.append(paths.log_md)
    else:
        skipped.append(paths.log_md)

    # seed concept pages
    seeded = 0
    if with_seed:
        seed_concepts = seed_dir() / "concepts"
        if seed_concepts.is_dir():
            for src in sorted(seed_concepts.glob("*.md")):
                dst = paths.concepts / src.name
                if force or not dst.exists():
                    if force:
                        _backup_then_overwrite(dst, backups=backups)
                    shutil.copy2(src, dst)
                    created.append(dst)
                    seeded += 1
                else:
                    skipped.append(dst)

        _index_existing_wiki_pages(paths)

    return InitResult(created=created, skipped=skipped, seeded_concepts=seeded, backups=backups)


def _index_existing_wiki_pages(paths: WikiPaths) -> None:
    """Populate wiki_index for pages present after init.

    `kairos init` is the first command most users run. If it seeds concept
    pages but leaves the cache empty, selector/query fall back to filesystem
    walks until a later ingest happens. Index all valid seed/existing pages so
    the cache is useful immediately.
    """
    indexer = WikiIndexer(db_path=paths.db)
    seen_slugs: set[str] = set()
    for folder in (paths.concepts, paths.sources, paths.comparisons):
        for page in sorted(folder.glob("*.md")):
            parsed = None
            try:
                parsed = parse_page(page.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                print(f"[init] skipped indexing malformed page {page}: {exc}", file=sys.stderr)
            if parsed is None:
                continue
            fm, body = parsed
            rel = page.relative_to(paths.root).as_posix()
            slug = page.stem
            seen_slugs.add(slug)
            previous = indexer.lookup(slug)
            indexer.upsert_page(slug=slug, fm=fm, body=body, file_rel=rel)
            indexer.upsert_relations(
                from_slug=slug,
                links=extract_wikilinks(body),
                related=fm.related,
            )
            if previous and previous.get("file") != rel:
                indexer.remove_page(str(previous["slug"]))
                indexer.upsert_page(slug=slug, fm=fm, body=body, file_rel=rel)
                indexer.upsert_relations(
                    from_slug=slug,
                    links=extract_wikilinks(body),
                    related=fm.related,
                )
    for row in indexer.all_pages():
        slug = str(row.get("slug", ""))
        file_rel = row.get("file")
        if slug and (slug not in seen_slugs or not isinstance(file_rel, str) or not (paths.root / file_rel).exists()):
            indexer.remove_page(slug)


def _minimal_agents_stub() -> str:
    return (
        "# Kairos Wiki Schema (stub)\n\n"
        "_(seed schema missing - this is a fallback. Run `kairos init --force` "
        "after reinstalling the package.)_\n\n"
        "## Project structure\n\n"
        "- `raw/` - Immutable sources.\n"
        "- `wiki/` - LLM-generated pages.\n"
        "- `outputs/` - Lint reports, run transcripts.\n"
        "- `.kairos/kairos.db` - Local state.\n\n"
        "## Workflows\n\n"
        "Ingest, query, lint, run.\n"
    )
