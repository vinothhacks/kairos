"""SQLite wrapper. Always opens with foreign_keys=ON."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Database:
    """Tiny SQLite façade with auto-migrating schema."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ensure_schema(self.path)
        _apply_concurrency_pragmas(self.path)

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.path, timeout=5.0)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON;")
        c.execute("PRAGMA busy_timeout = 5000;")
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def insert_run(
        self,
        *,
        task: str,
        technique: str,
        selected_by: str,
        selector_score: float | None,
        status: str,
        duration_ms: float | None,
        cost_tokens: int | None = None,
        answer_path: str | None = None,
        trace_path: str | None = None,
        error_msg: str | None = None,
    ) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO runs(task, technique, selected_by, selector_score, status, duration_ms, "
                "cost_tokens, answer_path, trace_path, error_msg) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task,
                    technique,
                    selected_by,
                    selector_score,
                    status,
                    duration_ms,
                    cost_tokens,
                    answer_path,
                    trace_path,
                    error_msg,
                ),
            )
            return int(cur.lastrowid or 0)

    def list_runs(self, limit: int = 20) -> list[sqlite3.Row]:
        with self.conn() as c:
            cur = c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
            return list(cur.fetchall())

    def insert_feedback(
        self, *, run_id: int, rating: int, note: str | None = None
    ) -> int:
        """KAI-035: persist user feedback against a previous run.

        Returns the SQLite implicit rowid of the new row. The feedback table
        uses (run_id, ts) as its composite PK, so the rowid is the only stable
        per-row id we can hand back.
        """
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO feedback(run_id, rating, note) VALUES (?, ?, ?)",
                (run_id, rating, note),
            )
            return int(cur.lastrowid or 0)

    def list_feedback(self, *, run_id: int | None = None) -> list[sqlite3.Row]:
        with self.conn() as c:
            if run_id is None:
                cur = c.execute("SELECT rowid AS id, * FROM feedback ORDER BY rowid DESC")
            else:
                cur = c.execute(
                    "SELECT rowid AS id, * FROM feedback WHERE run_id = ? ORDER BY rowid DESC",
                    (run_id,),
                )
            return list(cur.fetchall())


def ensure_schema(db_path: Path) -> None:
    """Run schema.sql against the given SQLite file."""
    schema_sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path)
    try:
        c.executescript(schema_sql)
        c.commit()
    finally:
        c.close()


def _apply_concurrency_pragmas(db_path: Path) -> None:
    """KAI-022: enable WAL + sane synchronous + busy_timeout for multi-process safety.

    WAL is sticky: once set on a database file, it persists across opens. We
    still set it every __post_init__ to handle freshly-created files. journal_mode
    can fall back to DELETE on filesystems that do not support WAL (network FS),
    which is fine - the busy_timeout still protects writers.
    """
    c = sqlite3.connect(db_path, timeout=5.0)
    try:
        c.execute("PRAGMA journal_mode = WAL;")
        c.execute("PRAGMA synchronous = NORMAL;")
        c.execute("PRAGMA busy_timeout = 5000;")
        c.commit()
    finally:
        c.close()
