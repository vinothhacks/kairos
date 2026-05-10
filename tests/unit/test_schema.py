"""Schema parser + frontmatter round-trip tests."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from textwrap import dedent

import pytest

from kairos.wiki.schema import (
    PageFrontmatter,
    extract_wikilinks,
    parse_page,
    render_page,
    validate_schema_loaded,
)


def test_parse_page_minimal() -> None:
    text = dedent(
        """\
        ---
        title: ReAct
        type: concept
        created: 2026-04-01
        updated: 2026-04-15
        confidence: high
        ---

        # ReAct

        Body text.
        """
    )
    fm, body = parse_page(text)
    assert fm.title == "ReAct"
    assert fm.type == "concept"
    assert fm.confidence == "high"
    assert fm.created == _dt.date(2026, 4, 1)
    assert body.startswith("# ReAct")


def test_parse_page_with_lists() -> None:
    text = dedent(
        """\
        ---
        title: RAG
        type: concept
        created: 2026-04-01
        updated: 2026-04-15
        confidence: medium
        sources:
          - raw/papers/lewis-2020.md
        related:
          - "[[react]]"
          - "[[reflexion]]"
        has_runner: true
        ---
        body
        """
    )
    fm, _ = parse_page(text)
    assert fm.has_runner is True
    assert fm.sources == ["raw/papers/lewis-2020.md"]
    assert fm.related == ["[[react]]", "[[reflexion]]"]


def test_parse_page_missing_frontmatter_raises() -> None:
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_page("# Just a title\n\nbody")


def test_parse_page_invalid_type_raises() -> None:
    text = dedent(
        """\
        ---
        title: x
        type: bogus
        created: 2026-04-01
        updated: 2026-04-01
        ---
        body
        """
    )
    with pytest.raises(ValueError, match="invalid page type"):
        parse_page(text)


def test_render_frontmatter_round_trip() -> None:
    fm = PageFrontmatter(
        title="ReAct",
        type="concept",
        created=_dt.date(2026, 4, 1),
        updated=_dt.date(2026, 4, 15),
        confidence="high",
        related=["[[rag]]"],
        has_runner=True,
    )
    text = render_page(fm, "Body text.\n")
    fm2, body = parse_page(text)
    assert fm2.title == fm.title
    assert fm2.has_runner is True
    assert fm2.related == ["[[rag]]"]
    assert body.strip() == "Body text."


def test_extract_wikilinks() -> None:
    body = "See [[react]] and [[rag|Retrieval]] but not [[]] empty."
    links = extract_wikilinks(body)
    assert links == ["react", "rag"]


def test_validate_schema_loaded_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        validate_schema_loaded(tmp_path)


def test_validate_schema_loaded_invalid(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Not a valid schema\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required sections"):
        validate_schema_loaded(tmp_path)


def test_validate_schema_loaded_ok(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "# Schema\n\n## Project structure\n\n- raw/\n\n## Workflows\n\nIngest, query.\n",
        encoding="utf-8",
    )
    validate_schema_loaded(tmp_path)
