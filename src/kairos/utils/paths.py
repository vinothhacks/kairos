"""Filesystem path helpers.

v0.2 (KAI-018): when `KAIROS_DB_HOME` is set, the SQLite database path moves to
that directory (the wiki itself stays under `<project>/`). This matches the
`docs/architecture.md` claim and lets users keep their state out of the repo.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikiPaths:
    """Resolved paths for a kairos project rooted at `root`."""

    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).expanduser().resolve())

    @property
    def agents_md(self) -> Path:
        return self.root / "AGENTS.md"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def wiki(self) -> Path:
        return self.root / "wiki"

    @property
    def index_md(self) -> Path:
        return self.wiki / "index.md"

    @property
    def log_md(self) -> Path:
        return self.wiki / "log.md"

    @property
    def concepts(self) -> Path:
        return self.wiki / "concepts"

    @property
    def sources(self) -> Path:
        return self.wiki / "sources"

    @property
    def comparisons(self) -> Path:
        return self.wiki / "comparisons"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def state_dir(self) -> Path:
        return self.root / ".kairos"

    @property
    def db(self) -> Path:
        # KAI-018: honor KAIROS_DB_HOME if set, so users can keep .kairos/kairos.db
        # outside the repo. Default stays <project>/.kairos/kairos.db.
        override = os.environ.get("KAIROS_DB_HOME", "").strip()
        if override:
            project_hash = hashlib.sha256(str(self.root).encode("utf-8")).hexdigest()[:12]
            return Path(override).expanduser().resolve() / project_hash / "kairos.db"
        return self.state_dir / "kairos.db"

    def ensure_dirs(self) -> None:
        for d in (
            self.raw,
            self.raw / "articles",
            self.raw / "papers",
            self.wiki,
            self.concepts,
            self.sources,
            self.comparisons,
            self.outputs,
            self.state_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


def resolve_root(start: Path | None = None) -> Path:
    """Walk upward looking for AGENTS.md; fall back to the given start dir."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "AGENTS.md").exists() and (candidate / "wiki").is_dir():
            return candidate
    return here


def seed_dir() -> Path:
    """Where the bundled seed wiki lives inside the installed package."""
    return Path(__file__).resolve().parent.parent / "_seed"
