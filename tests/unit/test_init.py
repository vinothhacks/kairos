"""kairos init bootstrap tests."""
from __future__ import annotations

from pathlib import Path

from kairos.wiki.init import init_project


def test_init_creates_layout(tmp_path: Path) -> None:
    result = init_project(tmp_path, with_seed=False)
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "raw" / "articles").is_dir()
    assert (tmp_path / "raw" / "papers").is_dir()
    assert (tmp_path / "wiki" / "index.md").exists()
    assert (tmp_path / "wiki" / "log.md").exists()
    assert (tmp_path / "wiki" / "concepts").is_dir()
    assert (tmp_path / "wiki" / "sources").is_dir()
    assert (tmp_path / "wiki" / "comparisons").is_dir()
    assert (tmp_path / "outputs").is_dir()
    assert (tmp_path / ".kairos").is_dir()
    assert (tmp_path / "AGENTS.md") in result.created
    assert result.skipped == []


def test_init_idempotent_without_force(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    second = init_project(tmp_path, with_seed=False)
    assert (tmp_path / "AGENTS.md") in second.skipped
    assert (tmp_path / "wiki" / "index.md") in second.skipped


def test_init_force_overwrites(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    custom = "## custom user edit\n"
    (tmp_path / "wiki" / "log.md").write_text(custom, encoding="utf-8")
    init_project(tmp_path, force=True, with_seed=False)
    assert "init | wiki bootstrapped" in (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")


def test_init_log_has_today_entry(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    log = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "init | wiki bootstrapped" in log


def test_init_index_lists_empty_sections(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    index = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "Concepts" in index
    assert "Sources" in index
    assert "Comparisons" in index
