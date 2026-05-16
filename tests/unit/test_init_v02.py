"""KAI-001 regression tests: kairos init --force must not silently destroy user content."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from kairos.wiki.init import init_project


def test_force_backs_up_user_log(tmp_path: Path) -> None:
    """KAI-001: --force must write a .bak before overwriting user-edited log.md."""
    init_project(tmp_path, with_seed=False)
    log_path = tmp_path / "wiki" / "log.md"
    custom = "# my custom log\n\nuser-curated content here\n"
    log_path.write_text(custom, encoding="utf-8")

    init_project(tmp_path, force=True, with_seed=False)

    backups = list(log_path.parent.glob("log.md.bak*"))
    assert len(backups) == 1, f"expected exactly one log.md.bak*, found {backups}"
    assert custom in backups[0].read_text(encoding="utf-8")


def test_force_backs_up_user_index(tmp_path: Path) -> None:
    """KAI-001: --force must back up user-edited index.md."""
    init_project(tmp_path, with_seed=False)
    index_path = tmp_path / "wiki" / "index.md"
    custom = "# my custom index\n\nuser content\n"
    index_path.write_text(custom, encoding="utf-8")

    init_project(tmp_path, force=True, with_seed=False)

    backups = list(index_path.parent.glob("index.md.bak*"))
    assert len(backups) == 1
    assert custom in backups[0].read_text(encoding="utf-8")


def test_force_backs_up_user_agents_md(tmp_path: Path) -> None:
    """KAI-001: --force must back up user-edited AGENTS.md."""
    init_project(tmp_path, with_seed=False)
    agents = tmp_path / "AGENTS.md"
    custom = "# Custom Schema\n\nuser tweaks here\n"
    agents.write_text(custom, encoding="utf-8")

    init_project(tmp_path, force=True, with_seed=False)

    backups = list(agents.parent.glob("AGENTS.md.bak*"))
    assert len(backups) == 1
    assert custom in backups[0].read_text(encoding="utf-8")


def test_force_does_not_create_bak_when_target_did_not_exist(tmp_path: Path) -> None:
    """No backup file should be created when there was nothing to back up."""
    init_project(tmp_path, force=True, with_seed=False)
    bak_files = list((tmp_path / "wiki").glob("*.bak*"))
    assert bak_files == []


def test_init_indexes_seed_concepts_in_wiki_index(tmp_path: Path) -> None:
    """KAI2-002: init must populate wiki_index for the bundled seed pages."""
    result = init_project(tmp_path)
    assert result.seeded_concepts >= 21

    with sqlite3.connect(tmp_path / ".kairos" / "kairos.db") as conn:
        count = conn.execute("SELECT COUNT(*) FROM wiki_index WHERE type='concept'").fetchone()[0]
        relation_count = conn.execute("SELECT COUNT(*) FROM wiki_relations").fetchone()[0]

    assert count >= result.seeded_concepts
    assert relation_count > 0
