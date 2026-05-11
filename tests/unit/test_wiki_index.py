"""KAI-005 regression tests: wiki_index and wiki_relations tables must be populated."""
from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path

from kairos.memory.wiki_index import WikiIndexer
from kairos.utils.paths import WikiPaths
from kairos.wiki.init import init_project
from kairos.wiki.schema import PageFrontmatter


def _today() -> _dt.date:
    return _dt.date.today()


def test_upsert_page_writes_row(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    paths = WikiPaths(root=tmp_path)
    indexer = WikiIndexer(db_path=paths.db)

    page_path = paths.concepts / "react.md"
    page_path.write_text("dummy", encoding="utf-8")
    fm = PageFrontmatter(
        title="ReAct",
        type="concept",
        created=_today(),
        updated=_today(),
        confidence="high",
        has_runner=True,
    )
    indexer.upsert_page(slug="react", fm=fm, body="word1 word2 word3", file_rel="wiki/concepts/react.md")

    with sqlite3.connect(paths.db) as c:
        row = c.execute(
            "SELECT slug, type, file, title, has_runner, confidence, word_count FROM wiki_index WHERE slug=?",
            ("react",),
        ).fetchone()
    assert row is not None
    assert row[0] == "react"
    assert row[1] == "concept"
    assert row[2] == "wiki/concepts/react.md"
    assert row[3] == "ReAct"
    assert row[4] == 1  # has_runner stored as INTEGER
    assert row[5] == "high"
    assert row[6] == 3  # word count


def test_upsert_relations_writes_rows(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    paths = WikiPaths(root=tmp_path)
    indexer = WikiIndexer(db_path=paths.db)

    fm = PageFrontmatter(title="A", type="concept", created=_today(), updated=_today())
    indexer.upsert_page(slug="a", fm=fm, body="", file_rel="wiki/concepts/a.md")
    indexer.upsert_page(slug="b", fm=fm, body="", file_rel="wiki/concepts/b.md")
    indexer.upsert_page(slug="c", fm=fm, body="", file_rel="wiki/concepts/c.md")

    indexer.upsert_relations(from_slug="a", links=["b"], related=["[[c]]"])

    with sqlite3.connect(paths.db) as c:
        rows = c.execute(
            "SELECT from_slug, to_slug, kind FROM wiki_relations WHERE from_slug=? ORDER BY to_slug, kind",
            ("a",),
        ).fetchall()
    targets = {(r[1], r[2]) for r in rows}
    assert ("b", "wikilink") in targets
    assert ("c", "related") in targets


def test_upsert_page_idempotent(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    paths = WikiPaths(root=tmp_path)
    indexer = WikiIndexer(db_path=paths.db)
    fm = PageFrontmatter(title="X", type="concept", created=_today(), updated=_today())
    indexer.upsert_page(slug="x", fm=fm, body="hello world", file_rel="wiki/concepts/x.md")
    indexer.upsert_page(slug="x", fm=fm, body="hello world updated again", file_rel="wiki/concepts/x.md")

    with sqlite3.connect(paths.db) as c:
        rows = c.execute("SELECT word_count FROM wiki_index WHERE slug=?", ("x",)).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 4  # latest word count
