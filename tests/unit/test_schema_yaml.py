"""KAI-016 regression test: YAML 1.1 booleans (`no`, `off`, `on`) must not silently
become Python booleans in frontmatter that expects strings."""
from __future__ import annotations

from kairos.wiki.schema import parse_page


def test_yaml_norway_problem_in_related_field_handled() -> None:
    """When `related:` contains a bare `no`/`yes` (YAML booleans), parsing must
    not crash and the values must round-trip as lowercase literal strings.
    """
    text = (
        "---\n"
        "title: Test\n"
        "type: concept\n"
        "created: 2026-04-01\n"
        "updated: 2026-04-01\n"
        "confidence: medium\n"
        "related:\n"
        "  - no\n"
        "  - yes\n"
        "  - actual-page\n"
        "---\n\nbody\n"
    )
    fm, _ = parse_page(text)
    assert "actual-page" in fm.related
    assert "no" in fm.related, f"expected 'no' in related, got: {fm.related}"
    assert "yes" in fm.related, f"expected 'yes' in related, got: {fm.related}"


def test_yaml_norway_problem_in_sources_field_handled() -> None:
    """`off` is YAML 1.1 False; we coerce to the lowercase literal string 'no'."""
    text = (
        "---\n"
        "title: Test\n"
        "type: source\n"
        "created: 2026-04-01\n"
        "updated: 2026-04-01\n"
        "confidence: medium\n"
        "sources:\n"
        "  - off\n"
        "  - raw/articles/x.md\n"
        "---\n\nbody\n"
    )
    fm, _ = parse_page(text)
    assert "raw/articles/x.md" in fm.sources
    assert "no" in fm.sources, f"expected 'no' (False -> 'no'), got: {fm.sources}"
