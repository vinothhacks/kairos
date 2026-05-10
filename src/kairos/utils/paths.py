"""Filesystem path helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikiPaths:
    """Resolved paths for a kairos project rooted at `root`."""

    root: Path

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
