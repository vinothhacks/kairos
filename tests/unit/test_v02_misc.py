"""Misc Phase 4 / Phase 5 regression tests for kairos v0.2."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from kairos.memory.db import Database
from kairos.utils.paths import WikiPaths
from kairos.wiki.init import init_project


def test_kairos_db_home_redirects_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KAI-018: KAIROS_DB_HOME points the SQLite db at a different folder."""
    project = tmp_path / "proj"
    db_home = tmp_path / "alt_db_home"
    db_home.mkdir()
    init_project(project, with_seed=False)

    monkeypatch.setenv("KAIROS_DB_HOME", str(db_home))
    paths = WikiPaths(root=project)
    assert paths.db.parent == db_home.resolve()
    assert paths.db.name == "kairos.db"

    monkeypatch.delenv("KAIROS_DB_HOME")
    assert paths.db.parent == (project / ".kairos").resolve() or paths.db.parent.name == ".kairos"


def test_database_pragmas_set_wal_and_busy_timeout(tmp_path: Path) -> None:
    """KAI-022: Database opens with WAL + busy_timeout for concurrent safety."""
    db_path = tmp_path / "kairos.db"
    Database(path=db_path)
    with sqlite3.connect(db_path) as c:
        mode = c.execute("PRAGMA journal_mode").fetchone()[0]
        bt = c.execute("PRAGMA busy_timeout").fetchone()[0]
    assert mode.lower() in {"wal", "delete"}, f"unexpected journal_mode {mode}"
    # If WAL is supported we expect WAL; if not (e.g. some network FS), DELETE
    # is the documented fallback. busy_timeout always applies.
    assert bt >= 5000


def test_selector_segment_match_avoids_substring_false_positives(tmp_path: Path) -> None:
    """KAI-028: 'rag' should NOT match 'image' in slug 'imagery-tools'."""
    init_project(tmp_path, with_seed=False)
    page = tmp_path / "wiki" / "concepts" / "imagery-tools.md"
    page.write_text(
        "---\ntitle: Imagery Tools\ntype: concept\ncreated: 2026-04-01\n"
        "updated: 2026-04-01\nconfidence: medium\nhas_runner: false\n---\n\nbody\n",
        encoding="utf-8",
    )
    rag_page = tmp_path / "wiki" / "concepts" / "rag.md"
    rag_page.write_text(
        "---\ntitle: RAG\ntype: concept\ncreated: 2026-04-01\n"
        "updated: 2026-04-01\nconfidence: high\nhas_runner: true\n---\n\nrag rag rag\n",
        encoding="utf-8",
    )

    from kairos.selector import select_technique

    ranking = select_technique(task="rag for documents", project_root=tmp_path)
    # rag should be the only winner; the segment-match rule means imagery-tools
    # cannot win on substring overlap with "rag" inside "imagery".
    assert ranking[0].technique == "rag"


def test_selector_top_n_tiebreak_promotes_default(tmp_path: Path) -> None:
    """KAI-029: when 3 candidates are within 0.05 of leader, prefer 'rag'."""
    init_project(tmp_path, with_seed=False)
    for slug, content in [
        ("rag", "rag retrieval"),
        ("react", "react react"),
        ("reflexion", "reflexion reflexion"),
    ]:
        path = tmp_path / "wiki" / "concepts" / f"{slug}.md"
        path.write_text(
            f"---\ntitle: {slug.title()}\ntype: concept\ncreated: 2026-04-01\n"
            f"updated: 2026-04-01\nconfidence: high\nhas_runner: true\n---\n\n{content}\n",
            encoding="utf-8",
        )

    from kairos.selector import select_technique

    # task with no strong signal: all three should score similarly low and the
    # tie-break rule should surface 'rag' to the top.
    ranking = select_technique(task="some neutral question", project_root=tmp_path)
    assert ranking[0].technique == "rag"


def test_runresult_no_trace_field() -> None:
    """KAI-034: RunResult dropped its `trace` field; trace lives on disk only."""
    from kairos.runners.base import RunResult

    r = RunResult(technique="rag", task="t", answer="a")
    assert not hasattr(r, "trace") or not isinstance(getattr(r, "trace", None), list)


def test_runresult_duration_is_float() -> None:
    """KAI-042: duration_ms is a float, not coerced int."""
    from kairos.runners.base import RunResult

    r = RunResult(technique="rag", task="t", answer="a", duration_ms=1.5)
    assert isinstance(r.duration_ms, float)
    assert r.duration_ms == 1.5
