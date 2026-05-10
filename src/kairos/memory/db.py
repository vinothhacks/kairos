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

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON;")
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
        duration_ms: int | None,
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
