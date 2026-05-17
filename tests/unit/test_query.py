"""kairos query tests."""
from __future__ import annotations

import json
from pathlib import Path

from kairos.llm.providers import StubLLMClient
from kairos.wiki.init import init_project
from kairos.wiki.query import query_wiki


def _seed_wiki(root: Path) -> None:
    init_project(root, with_seed=False)
    (root / "wiki" / "concepts" / "react.md").write_text(
        "---\n"
        "title: ReAct\n"
        "type: concept\n"
        "created: 2026-04-01\n"
        "updated: 2026-04-15\n"
        "confidence: high\n"
        "related:\n"
        "  - \"[[reflexion]]\"\n"
        "---\n\n"
        "## Summary\n\nReAct interleaves reasoning and tool use. Best for tasks that need search.\n",
        encoding="utf-8",
    )
    (root / "wiki" / "concepts" / "reflexion.md").write_text(
        "---\n"
        "title: Reflexion\n"
        "type: concept\n"
        "created: 2026-04-01\n"
        "updated: 2026-04-15\n"
        "confidence: high\n"
        "related:\n"
        "  - \"[[react]]\"\n"
        "---\n\n"
        "## Summary\n\nReflexion adds a self-critique loop on top of an initial answer.\n",
        encoding="utf-8",
    )


def test_query_picks_relevant_pages_and_logs(tmp_path: Path) -> None:
    _seed_wiki(tmp_path)

    canned_path = tmp_path / "stub.json"
    canned_path.write_text(
        json.dumps(
            {
                "claude_send::You are answering a question grounded in this w": "ReAct interleaves reasoning and tool use.\n\n## Sources\n\n- [[react]]"
            }
        ),
        encoding="utf-8",
    )
    llm = StubLLMClient(stub_path=canned_path)

    result = query_wiki("When should I use ReAct?", project_root=tmp_path, llm=llm)
    assert "ReAct" in result.answer
    pages = {p.stem for p in result.pages_read}
    assert "react" in pages
    log = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "When should I use ReAct?" in log


def test_query_returns_useful_message_when_no_pages(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    llm = StubLLMClient()
    result = query_wiki("What is X?", project_root=tmp_path, llm=llm)
    assert result.pages_read == []
    assert "stub:claude_send" in result.answer.lower() or len(result.answer) > 0


def test_query_save_to_wiki_creates_q_page(tmp_path: Path) -> None:
    _seed_wiki(tmp_path)
    canned_path = tmp_path / "stub.json"
    canned_path.write_text(
        json.dumps(
            {
                "claude_send::You are answering a question grounded in this w": "Use [[react]] when you need to search."
            }
        ),
        encoding="utf-8",
    )
    llm = StubLLMClient(stub_path=canned_path)
    result = query_wiki("When should I use ReAct?", project_root=tmp_path, llm=llm, save_to_wiki=True)
    assert result.saved_to is not None
    assert result.saved_to.exists()
    text = result.saved_to.read_text(encoding="utf-8")
    assert "When should I use ReAct?" in text
    assert "[[react]]" in text
