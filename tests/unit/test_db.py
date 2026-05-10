"""Memory layer (SQLite) tests."""
from __future__ import annotations

from pathlib import Path

from kairos.memory.db import Database, ensure_schema


def test_ensure_schema_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "kairos.db"
    ensure_schema(db_path)
    db = Database(path=db_path)
    with db.conn() as c:
        rows = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r["name"] for r in rows}
    assert {"runs", "feedback", "wiki_index", "wiki_relations"} <= names


def test_insert_and_list_runs(tmp_path: Path) -> None:
    db = Database(path=tmp_path / "kairos.db")
    rid = db.insert_run(
        task="What is X?",
        technique="rag",
        selected_by="selector",
        selector_score=0.42,
        status="ok",
        duration_ms=1234,
    )
    assert rid >= 1
    rows = db.list_runs()
    assert rows[0]["task"] == "What is X?"
    assert rows[0]["technique"] == "rag"
    assert rows[0]["status"] == "ok"
