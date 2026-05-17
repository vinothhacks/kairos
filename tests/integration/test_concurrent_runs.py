"""KAI-031: concurrent run inserts must not corrupt the SQLite db.

We exercise the WAL + busy_timeout pragmas (KAI-022) by spawning N worker
threads that each call `dispatch` on the same project. The wins:

- All N rows land cleanly (count(*) == N).
- Each row has a distinct id (no double-inserts, no rollbacks).
- The database file is still readable afterwards (no corruption).

Threads are sufficient: SQLite's WAL mode allows multiple readers + one
writer concurrently per process, and Database.conn() opens a fresh
connection per call so each thread has its own writer handle.
"""
from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from kairos.llm.providers import StubLLMClient
from kairos.runners import dispatch
from kairos.wiki.init import init_project


@pytest.mark.integration
def test_dispatch_handles_concurrent_writes(tmp_path: Path) -> None:
    """4 threads run a stubbed RAG dispatch in parallel; all rows land cleanly."""
    init_project(tmp_path, with_seed=False)
    # rag runner needs at least one concept page on disk
    (tmp_path / "wiki" / "concepts" / "rag.md").write_text(
        "---\ntitle: RAG\ntype: concept\ncreated: 2026-04-01\nupdated: 2026-04-01\nconfidence: high\nhas_runner: true\n---\n\n## Summary\n\nRetrieval augmented generation.\n",
        encoding="utf-8",
    )
    llm = StubLLMClient()

    n_workers = 4

    def _do_run(i: int) -> int:
        result = dispatch(
            "rag",
            task=f"task-{i}",
            project_root=tmp_path,
            llm=llm,
            selected_by="selector",
            selector_score=0.5,
        )
        assert result.run_id is not None
        return result.run_id

    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        run_ids = list(ex.map(_do_run, range(n_workers)))

    # Every dispatch produced a unique row id, no rollbacks, no double-counts.
    assert len(set(run_ids)) == n_workers, f"expected {n_workers} distinct ids, got {sorted(run_ids)}"

    # And the db itself is still queryable.
    db_path = tmp_path / ".kairos" / "kairos.db"
    with sqlite3.connect(db_path) as c:
        c.row_factory = sqlite3.Row
        rows = list(c.execute("SELECT id, task, status FROM runs ORDER BY id"))
    assert len(rows) == n_workers
    assert all(r["status"] == "ok" for r in rows)
    assert {r["task"] for r in rows} == {f"task-{i}" for i in range(n_workers)}
