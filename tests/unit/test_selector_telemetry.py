"""KAI-008 / KAI-030 regression tests: auto-selected runs record selector telemetry."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from kairos.llm.providers import StubLLMClient
from kairos.runners import dispatch
from kairos.wiki.init import init_project


def test_dispatch_records_selected_by_selector(tmp_path: Path) -> None:
    """KAI-008: when CLI auto-selects a runner, runs.selected_by must be 'selector'."""
    init_project(tmp_path, with_seed=False)
    llm = StubLLMClient()

    dispatch(
        "rag",
        task="any task",
        project_root=tmp_path,
        llm=llm,
        selected_by="selector",
        selector_score=0.42,
    )

    db_path = tmp_path / ".kairos" / "kairos.db"
    with sqlite3.connect(db_path) as c:
        c.row_factory = sqlite3.Row
        rows = list(c.execute("SELECT selected_by, selector_score FROM runs ORDER BY id DESC LIMIT 1"))
    assert len(rows) == 1
    assert rows[0]["selected_by"] == "selector"
    assert rows[0]["selector_score"] is not None
    assert abs(float(rows[0]["selector_score"]) - 0.42) < 1e-6


def test_dispatch_user_pinned_run_keeps_user_label(tmp_path: Path) -> None:
    """When --technique is explicit, selected_by stays 'user' and score is NULL."""
    init_project(tmp_path, with_seed=False)
    llm = StubLLMClient()

    dispatch(
        "rag",
        task="another task",
        project_root=tmp_path,
        llm=llm,
        selected_by="user",
        selector_score=None,
    )

    db_path = tmp_path / ".kairos" / "kairos.db"
    with sqlite3.connect(db_path) as c:
        c.row_factory = sqlite3.Row
        rows = list(c.execute("SELECT selected_by, selector_score FROM runs ORDER BY id DESC LIMIT 1"))
    assert rows[0]["selected_by"] == "user"
    assert rows[0]["selector_score"] is None
