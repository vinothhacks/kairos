"""KAI-002 + KAI-003 + KAI-024 regression tests for ingest pipeline."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from kairos.llm.mcp_client import StubLLMClient
from kairos.wiki.ingest import ingest_file
from kairos.wiki.init import init_project
from kairos.wiki.schema import parse_page


def _canned(tmp_path: Path, plan: Mapping[str, object]) -> StubLLMClient:
    canned_path = tmp_path / "stub.json"
    canned_path.write_text(
        json.dumps({"claude_send::You are the wiki maintainer for a kairos pr": json.dumps(plan)}),
        encoding="utf-8",
    )
    return StubLLMClient(stub_path=canned_path)


def _basic_plan(title: str = "Source", concept_slug: str = "src") -> dict[str, object]:
    return {
        "source_page": {
            "title": title,
            "body": "## TL;DR\n\nbody\n",
            "related": [],
            "confidence": "medium",
        },
        "concept_updates": [
            {
                "slug": concept_slug,
                "title": concept_slug.title(),
                "action": "create",
                "body": "## Summary\n\nbody\n",
                "confidence": "medium",
            }
        ],
    }


def test_reingest_with_changed_content_does_not_keep_stale_copy(tmp_path: Path) -> None:
    """KAI-002: re-ingesting an externally-edited source must not silently keep the stale raw/ copy."""
    init_project(tmp_path, with_seed=False)
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    src = external_dir / "doc.md"
    src.write_text("# Doc v1\n\nfirst version\n", encoding="utf-8")
    plan = _basic_plan(title="Doc v1", concept_slug="doc")
    llm = _canned(tmp_path, plan)
    ingest_file(src, project_root=tmp_path, llm=llm)

    # Edit the external source.
    src.write_text("# Doc v2\n\nupdated content here\n", encoding="utf-8")
    ingest_file(src, project_root=tmp_path, llm=llm)

    # We expect EITHER the raw copy was overwritten OR a new raw_2 file was created.
    raw_files = sorted((tmp_path / "raw" / "articles").glob("*.md"))
    contents = [p.read_text(encoding="utf-8") for p in raw_files]
    has_v2 = any("Doc v2" in c for c in contents)
    assert has_v2, f"expected raw/articles to contain Doc v2 after re-ingest; got files: {raw_files}"


def test_two_sources_with_same_title_do_not_collide(tmp_path: Path) -> None:
    """KAI-003: ingesting two sources with the same title must produce two distinct source pages."""
    init_project(tmp_path, with_seed=False)
    a = tmp_path / "external" / "a.md"
    a.parent.mkdir(parents=True)
    a.write_text("# Same Title\n\nbody A\n", encoding="utf-8")

    b = tmp_path / "external" / "b.md"
    b.write_text("# Same Title\n\nbody B\n", encoding="utf-8")

    plan = _basic_plan(title="Same Title", concept_slug="same-title")
    llm = _canned(tmp_path, plan)
    ingest_file(a, project_root=tmp_path, llm=llm)
    ingest_file(b, project_root=tmp_path, llm=llm)

    sources = sorted((tmp_path / "wiki" / "sources").glob("*.md"))
    assert len(sources) == 2, f"expected 2 source pages, got {len(sources)}: {sources}"


def test_reingest_preserves_created_date(tmp_path: Path) -> None:
    """KAI-024: re-ingesting must preserve the original `created` date of the source page."""
    init_project(tmp_path, with_seed=False)
    src = tmp_path / "external" / "x.md"
    src.parent.mkdir(parents=True)
    src.write_text("# Stable Title\n\nbody\n", encoding="utf-8")
    plan = _basic_plan(title="Stable Title", concept_slug="stable")
    llm = _canned(tmp_path, plan)

    first = ingest_file(src, project_root=tmp_path, llm=llm)
    fm_first, _ = parse_page(first.source_page.read_text(encoding="utf-8"))
    original_created = fm_first.created

    # Force the file mtime difference to trigger any re-ingest path.
    src.write_text("# Stable Title\n\nbody v2\n", encoding="utf-8")
    second = ingest_file(src, project_root=tmp_path, llm=llm)
    fm_second, _ = parse_page(second.source_page.read_text(encoding="utf-8"))

    assert fm_second.created == original_created, (
        f"created date changed on re-ingest: {original_created} -> {fm_second.created}"
    )
