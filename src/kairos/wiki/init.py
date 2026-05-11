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
from dataclasses import dataclass, field
from pathlib import Path

from kairos.utils.paths import WikiPaths, seed_dir

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

    return InitResult(created=created, skipped=skipped, seeded_concepts=seeded, backups=backups)


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
