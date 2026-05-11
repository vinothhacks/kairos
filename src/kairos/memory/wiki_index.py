"""WikiIndexer (KAI-005) - mirror wiki page metadata into SQLite.

Two tables already exist in `schema.sql` but were dead in v0.1:

  - wiki_index(slug, type, file, title, has_runner, confidence, updated,
               word_count, last_seen_ts)
  - wiki_relations(from_slug, to_slug, kind)

This module owns the WRITE path. Selector and query consume the cache (Phase 4 / KAI-021).
"""
from __future__ import annotations

import datetime as _dt
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from kairos.memory.db import ensure_schema
from kairos.wiki.schema import PageFrontmatter

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]+")
_WIKILINK_TARGET_RE = re.compile(r"^\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]$")


@dataclass
class WikiIndexer:
    """Tiny façade for the wiki_index + wiki_relations tables."""

    db_path: Path

    def __post_init__(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_schema(self.db_path)

    @staticmethod
    def _word_count(text: str) -> int:
        return sum(1 for _ in _WORD_RE.finditer(text))

    @staticmethod
    def _normalize_link(value: str) -> str:
        """Strip [[ ]] wrappers and aliases from a link target."""
        s = value.strip()
        m = _WIKILINK_TARGET_RE.match(s)
        if m:
            return m.group(1).strip()
        return s.strip("[]").split("|", 1)[0].strip()

    def upsert_page(
        self, *, slug: str, fm: PageFrontmatter, body: str, file_rel: str
    ) -> None:
        """Insert or update one wiki_index row."""
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                """
                INSERT INTO wiki_index
                  (slug, type, file, title, has_runner, confidence, updated, word_count, last_seen_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(slug) DO UPDATE SET
                  type=excluded.type,
                  file=excluded.file,
                  title=excluded.title,
                  has_runner=excluded.has_runner,
                  confidence=excluded.confidence,
                  updated=excluded.updated,
                  word_count=excluded.word_count,
                  last_seen_ts=datetime('now')
                """,
                (
                    slug,
                    fm.type,
                    file_rel,
                    fm.title,
                    1 if fm.has_runner else 0,
                    fm.confidence,
                    fm.updated.isoformat() if isinstance(fm.updated, _dt.date) else str(fm.updated),
                    self._word_count(body),
                ),
            )
            c.commit()

    def upsert_relations(
        self,
        *,
        from_slug: str,
        links: Iterable[str] = (),
        related: Iterable[str] = (),
    ) -> None:
        """Replace this page's outgoing relations.

        We delete-then-reinsert so removed wikilinks vanish from the cache.
        """
        link_targets = [self._normalize_link(s) for s in links if s]
        related_targets = [self._normalize_link(s) for s in related if s]
        with sqlite3.connect(self.db_path) as c:
            c.execute("PRAGMA foreign_keys = OFF;")  # we may insert before target slug exists
            c.execute("DELETE FROM wiki_relations WHERE from_slug=?", (from_slug,))
            for target in link_targets:
                if not target:
                    continue
                c.execute(
                    "INSERT OR IGNORE INTO wiki_relations(from_slug, to_slug, kind) VALUES (?, ?, 'wikilink')",
                    (from_slug, target),
                )
            for target in related_targets:
                if not target:
                    continue
                c.execute(
                    "INSERT OR IGNORE INTO wiki_relations(from_slug, to_slug, kind) VALUES (?, ?, 'related')",
                    (from_slug, target),
                )
            c.commit()

    def remove_page(self, slug: str) -> None:
        with sqlite3.connect(self.db_path) as c:
            c.execute("DELETE FROM wiki_relations WHERE from_slug=?", (slug,))
            c.execute("DELETE FROM wiki_index WHERE slug=?", (slug,))
            c.commit()

    def lookup(self, slug: str) -> dict[str, object] | None:
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            cur = c.execute("SELECT * FROM wiki_index WHERE slug=?", (slug,))
            row = cur.fetchone()
            return dict(row) if row else None

    def all_pages(self, kind: str | None = None) -> list[dict[str, object]]:
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            if kind:
                cur = c.execute("SELECT * FROM wiki_index WHERE type=? ORDER BY slug", (kind,))
            else:
                cur = c.execute("SELECT * FROM wiki_index ORDER BY slug")
            return [dict(r) for r in cur.fetchall()]


__all__ = ["WikiIndexer"]
