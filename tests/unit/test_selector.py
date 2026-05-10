"""Selector ranking tests."""
from __future__ import annotations

from pathlib import Path

from kairos.selector import select_technique
from kairos.wiki.init import init_project


def _seed_three_runners(root: Path) -> None:
    init_project(root, with_seed=False)
    for slug, summary in (
        ("rag", "RAG retrieves relevant context from a corpus and generates an answer. Best for summarize/document-grounded answers."),
        ("react", "ReAct interleaves reasoning and tool use. Best for tasks that need search, browsing, or multi-step investigation."),
        ("reflexion", "Reflexion adds a self-critique loop. Best when the model needs to verify and refine its own answer."),
    ):
        (root / "wiki" / "concepts" / f"{slug}.md").write_text(
            f"---\ntitle: {slug.upper()}\ntype: concept\ncreated: 2026-04-01\nupdated: 2026-04-15\nconfidence: high\nhas_runner: true\n---\n\n## Summary\n\n{summary}\n",
            encoding="utf-8",
        )


def test_selector_picks_react_for_search_task(tmp_path: Path) -> None:
    _seed_three_runners(tmp_path)
    out = select_technique(task="Find me the latest paper on tool-using agents on the web.", project_root=tmp_path)
    assert out[0].technique == "react"


def test_selector_picks_rag_for_summarize_task(tmp_path: Path) -> None:
    _seed_three_runners(tmp_path)
    out = select_technique(task="Summarize the notes in raw/ and cite sources.", project_root=tmp_path)
    assert out[0].technique == "rag"


def test_selector_picks_reflexion_for_critique_task(tmp_path: Path) -> None:
    _seed_three_runners(tmp_path)
    out = select_technique(task="Verify and critique my draft answer; refine and produce a polished version.", project_root=tmp_path)
    assert out[0].technique == "reflexion"


def test_selector_filters_pages_without_runner(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    (tmp_path / "wiki" / "concepts" / "tot.md").write_text(
        "---\ntitle: ToT\ntype: concept\ncreated: 2026-04-01\nupdated: 2026-04-15\nconfidence: high\n---\n\n## Summary\n\nTree of Thoughts. doc-only.\n",
        encoding="utf-8",
    )
    (tmp_path / "wiki" / "concepts" / "rag.md").write_text(
        "---\ntitle: RAG\ntype: concept\ncreated: 2026-04-01\nupdated: 2026-04-15\nconfidence: high\nhas_runner: true\n---\n\n## Summary\n\nrag.\n",
        encoding="utf-8",
    )
    out = select_technique(task="any task", project_root=tmp_path)
    techniques = {c.technique for c in out}
    assert "tot" not in techniques
    assert "rag" in techniques


def test_selector_falls_back_when_wiki_empty(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    out = select_technique(task="anything", project_root=tmp_path)
    assert len(out) == 1
    assert out[0].technique == "rag"
    assert "fallback" in out[0].rationale.lower()


def test_selector_returns_top3_ranked(tmp_path: Path) -> None:
    _seed_three_runners(tmp_path)
    out = select_technique(task="critique and verify the search results", project_root=tmp_path)
    assert len(out) >= 2
    # reflexion or react should win the critique-search hybrid; rag last
    assert out[-1].technique == "rag" or out[0].technique in {"reflexion", "react"}
