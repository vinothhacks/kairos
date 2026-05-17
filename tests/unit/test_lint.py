"""kairos lint tests."""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from kairos.llm.providers import StubLLMClient
from kairos.wiki.init import init_project
from kairos.wiki.lint import lint_wiki


def _make_page(root: Path, sub: str, slug: str, *, body: str = "## Summary\n\nbody.\n", related: list[str] | None = None, updated: str = "2026-04-15") -> None:
    related_block = ""
    if related:
        related_block = "related:\n" + "".join(f"  - \"{r}\"\n" for r in related)
    (root / "wiki" / sub).mkdir(parents=True, exist_ok=True)
    (root / "wiki" / sub / f"{slug}.md").write_text(
        f"---\n"
        f"title: {slug.replace('-', ' ').title()}\n"
        f"type: {'concept' if sub == 'concepts' else ('source' if sub == 'sources' else 'comparison')}\n"
        f"created: 2026-04-01\n"
        f"updated: {updated}\n"
        f"confidence: high\n"
        f"{related_block}"
        f"---\n\n{body}",
        encoding="utf-8",
    )


def test_lint_flags_missing_concept_targets(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    _make_page(tmp_path, "concepts", "react", body="See [[ghost-technique]] for related work.\n")
    llm = StubLLMClient()
    result = lint_wiki(project_root=tmp_path, llm=llm)
    kinds = {(f.kind, f.page) for f in result.findings}
    assert any(k[0] == "missing-concept" for k in kinds)


def test_lint_flags_orphan_concept(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    _make_page(tmp_path, "concepts", "lonely", body="## Summary\n\nNo links anywhere.\n")
    llm = StubLLMClient()
    result = lint_wiki(project_root=tmp_path, llm=llm)
    assert any(f.kind == "orphan" and f.page.endswith("lonely.md") for f in result.findings)


def test_lint_flags_stale_page(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    long_ago = (_dt.date.today() - _dt.timedelta(days=400)).isoformat()
    _make_page(tmp_path, "concepts", "old", updated=long_ago, related=["[[react]]"])
    _make_page(tmp_path, "concepts", "react", related=["[[old]]"])
    llm = StubLLMClient()
    result = lint_wiki(project_root=tmp_path, llm=llm, stale_after_days=180)
    assert any(f.kind == "stale" for f in result.findings)


def test_lint_flags_parse_error(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    (tmp_path / "wiki" / "concepts" / "broken.md").write_text("# no frontmatter at all\n", encoding="utf-8")
    llm = StubLLMClient()
    result = lint_wiki(project_root=tmp_path, llm=llm)
    assert any(f.kind == "parse-error" for f in result.findings)


def test_lint_writes_report(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    _make_page(tmp_path, "concepts", "x", related=["[[y]]"])
    _make_page(tmp_path, "concepts", "y", related=["[[x]]"])
    llm = StubLLMClient()
    result = lint_wiki(project_root=tmp_path, llm=llm)
    assert result.report_path.exists()
    text = result.report_path.read_text(encoding="utf-8")
    assert "kairos lint" in text


def test_lint_parses_llm_findings(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    _make_page(tmp_path, "concepts", "x", related=["[[y]]"])
    _make_page(tmp_path, "concepts", "y", related=["[[x]]"])
    canned_path = tmp_path / "stub.json"
    canned_path.write_text(
        json.dumps(
            {
                "claude_send::You are linting a wiki for contradictions": "- [high] contradiction | x.md, y.md | x says A, y says not-A\n- [medium] gap | x.md | missing failure modes section"
            }
        ),
        encoding="utf-8",
    )
    llm = StubLLMClient(stub_path=canned_path)
    result = lint_wiki(project_root=tmp_path, llm=llm)
    kinds = {f.kind for f in result.findings}
    assert "contradiction" in kinds
    assert "gap" in kinds
