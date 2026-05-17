"""kairos ingest tests using the stub LLM."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from kairos.llm.providers import StubLLMClient
from kairos.wiki.ingest import ingest_file, slugify
from kairos.wiki.init import init_project
from kairos.wiki.schema import parse_page


def _seed_canned(tmp_path: Path, plan: Mapping[str, object]) -> StubLLMClient:
    """Produce a StubLLMClient that returns `plan` (as JSON) on any claude_send call."""
    canned_path = tmp_path / "stub.json"
    canned_path.write_text(
        json.dumps({"claude_send::You are the wiki maintainer for a kairos pr": json.dumps(plan)}),
        encoding="utf-8",
    )
    return StubLLMClient(stub_path=canned_path)


def test_slugify_basic() -> None:
    assert slugify("Tree of Thoughts") == "tree-of-thoughts"
    assert slugify("RAG (Retrieval-Augmented Generation)") == "rag-retrieval-augmented-generation"
    assert slugify("") == "untitled"


def test_ingest_creates_source_page(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    src = tmp_path / "raw" / "articles" / "react-paper.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        "# ReAct: Synergizing Reasoning and Acting\n\nReAct interleaves thoughts and actions.\n",
        encoding="utf-8",
    )
    plan = {
        "source_page": {
            "title": "ReAct: Synergizing Reasoning and Acting",
            "body": "## TL;DR\n\nInterleaves reasoning and tool use.\n\n## Key claims\n\n- Reasoning + acting beats either alone (claim is: confirmed)\n",
            "related": ["[[react]]"],
            "confidence": "high",
        },
        "concept_updates": [
            {
                "slug": "react",
                "title": "ReAct",
                "action": "create",
                "body": "## Summary\n\nReAct interleaves reasoning and tool use.\n",
                "related": [],
                "sources": ["raw/articles/react-paper.md"],
                "confidence": "high",
                "has_runner": True,
            }
        ],
    }
    llm = _seed_canned(tmp_path, plan)
    result = ingest_file(src, project_root=tmp_path, llm=llm)
    assert result.source_page.exists()
    assert result.source_page.name == "react-synergizing-reasoning-and-acting.md"
    assert len(result.concept_pages_created) == 1
    react_page = result.concept_pages_created[0]
    fm, body = parse_page(react_page.read_text(encoding="utf-8"))
    assert fm.title == "ReAct"
    assert fm.has_runner is True
    assert "ReAct interleaves reasoning" in body


def test_ingest_updates_existing_concept_page(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)

    # Pre-create a concept page so the ingest treats it as an update.
    existing = tmp_path / "wiki" / "concepts" / "react.md"
    existing.write_text(
        "---\ntitle: ReAct\ntype: concept\ncreated: 2026-04-01\nupdated: 2026-04-01\nconfidence: medium\n---\n\n## Summary\n\nOriginal summary.\n",
        encoding="utf-8",
    )

    src = tmp_path / "raw" / "articles" / "newer-react.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("# ReAct follow-up\n\nNew finding: ReAct beats Reflexion on web tasks.\n", encoding="utf-8")

    plan = {
        "source_page": {
            "title": "ReAct follow-up",
            "body": "## TL;DR\n\nNew finding.\n",
            "related": ["[[react]]"],
            "confidence": "medium",
        },
        "concept_updates": [
            {
                "slug": "react",
                "title": "ReAct",
                "action": "update",
                "body": "## Update 2026-04-15\n\nNew finding: ReAct beats Reflexion on web tasks.\n",
                "related": ["[[reflexion]]"],
                "sources": ["raw/articles/newer-react.md"],
                "confidence": "high",
            }
        ],
    }
    llm = _seed_canned(tmp_path, plan)
    result = ingest_file(src, project_root=tmp_path, llm=llm)
    assert len(result.concept_pages_updated) == 1
    fm, body = parse_page(existing.read_text(encoding="utf-8"))
    assert "Original summary" in body
    assert "ReAct beats Reflexion" in body
    assert "[[reflexion]]" in fm.related


def test_ingest_caps_concept_updates(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    src = tmp_path / "raw" / "articles" / "many.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("# Many things\n\nbody\n", encoding="utf-8")
    big_plan = {
        "source_page": {"title": "Many things", "body": "## TL;DR\n\nbody\n", "related": [], "confidence": "low"},
        "concept_updates": [
            {"slug": f"concept-{i}", "title": f"Concept {i}", "action": "create", "body": "x", "confidence": "low"}
            for i in range(30)
        ],
    }
    llm = _seed_canned(tmp_path, big_plan)
    result = ingest_file(src, project_root=tmp_path, llm=llm, max_concept_updates=5)
    assert len(result.concept_pages_created) == 5


def test_ingest_appends_log(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    src = tmp_path / "raw" / "articles" / "x.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("# X\nbody\n", encoding="utf-8")
    plan = {
        "source_page": {"title": "X", "body": "## TL;DR\n\nbody\n", "related": [], "confidence": "low"},
        "concept_updates": [],
    }
    llm = _seed_canned(tmp_path, plan)
    ingest_file(src, project_root=tmp_path, llm=llm)
    log = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "ingest | X" in log


def test_ingest_falls_back_when_llm_returns_garbage(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    src = tmp_path / "raw" / "articles" / "broken.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("# Broken response test\n\nbody\n", encoding="utf-8")

    # canned response: not JSON, on purpose
    canned = {"claude_send::You are the wiki maintainer for a kairos pr": "I don't know how to JSON."}
    canned_path = tmp_path / "stub.json"
    canned_path.write_text(json.dumps(canned), encoding="utf-8")
    llm = StubLLMClient(stub_path=canned_path)

    result = ingest_file(src, project_root=tmp_path, llm=llm)
    assert result.source_page.exists()
    fm, body = parse_page(result.source_page.read_text(encoding="utf-8"))
    assert fm.confidence == "low"
    assert "TL;DR" in body
