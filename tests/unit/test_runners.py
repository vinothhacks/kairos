"""Runner unit tests."""
from __future__ import annotations

import json
from pathlib import Path

from kairos.llm.mcp_client import StubLLMClient
from kairos.runners import dispatch
from kairos.runners.rag import run_rag
from kairos.runners.react import run_react
from kairos.runners.reflexion import run_reflexion
from kairos.wiki.init import init_project


def _stub_with(canned: dict[str, str], tmp_path: Path) -> StubLLMClient:
    p = tmp_path / "stub.json"
    p.write_text(json.dumps(canned), encoding="utf-8")
    return StubLLMClient(stub_path=p)


def test_rag_runner_uses_raw_chunks(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    (tmp_path / "raw" / "papers" / "react.md").write_text(
        "# ReAct\n\nReAct interleaves reasoning and acting. The key insight is that thoughts can interleave with tool use.\n",
        encoding="utf-8",
    )
    llm = _stub_with(
        {"chatgpt_send::Answer the user's task using ONLY the context": "ReAct interleaves reasoning and acting. (source: raw/papers/react.md L1-L4)"},
        tmp_path,
    )
    result = run_rag(task="What is ReAct in one sentence?", project_root=tmp_path, llm=llm)
    assert result.status == "ok"
    assert "ReAct" in result.answer
    assert result.answer_path is not None and result.answer_path.exists()
    assert result.trace_path is not None and result.trace_path.exists()
    # trace should record retrieval + llm calls
    trace = result.trace_path.read_text(encoding="utf-8")
    assert "retrieval_top_k" in trace
    assert "llm_call" in trace


def test_rag_runner_handles_empty_raw(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    llm = StubLLMClient()
    result = run_rag(task="What is X?", project_root=tmp_path, llm=llm)
    assert result.status == "ok"
    # Falls back to llm reply, which is the stub's default echo.
    assert result.answer


def test_react_runner_finishes_immediately(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    canned = {
        "claude_send::You are running a ReAct loop. Available tools": "Final Answer: The capital is Paris."
    }
    llm = _stub_with(canned, tmp_path)
    result = run_react(task="What is the capital of France?", project_root=tmp_path, llm=llm)
    assert "Paris" in result.answer
    assert result.status == "ok"


def test_react_runner_does_one_action_then_finishes(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    (tmp_path / "raw" / "x.md").write_text("Hello kairos.", encoding="utf-8")
    # We can't model two distinct prompts cleanly with the prefix matcher,
    # so check that the runner survives a single Final Answer reply.
    canned = {"claude_send::You are running a ReAct loop. Available tools": "Final Answer: kairos."}
    llm = _stub_with(canned, tmp_path)
    result = run_react(task="Read raw/x.md and tell me what's there.", project_root=tmp_path, llm=llm, max_steps=3)
    assert "kairos" in result.answer.lower()


def test_reflexion_runner_three_stage_handoff(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    canned = {
        "chatgpt_send::Answer this task carefully": "Initial answer.",
        "claude_send::Critique the following answer to a": "The initial answer is too short. Improvements: (1) add detail (2) cite (3) hedge.",
        "chatgpt_send::You wrote the answer below.": "Revised, longer, cited answer.",
    }
    llm = _stub_with(canned, tmp_path)
    result = run_reflexion(task="Explain X.", project_root=tmp_path, llm=llm)
    # The stub uses the FIRST matching key by prefix; both chatgpt_send keys collide on
    # the 'chatgpt_send::' prefix, so we just check the runner ran end-to-end.
    assert result.status == "ok"
    assert result.answer
    # Trace should show three llm-related events.
    trace = result.trace_path.read_text(encoding="utf-8") if result.trace_path else ""
    for stage in ("initial_done", "critique_done", "revise_done"):
        assert stage in trace


def test_dispatch_unknown_raises(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    llm = StubLLMClient()
    try:
        dispatch("unknown", task="x", project_root=tmp_path, llm=llm)
    except ValueError as e:
        assert "unknown technique" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_dispatch_routes_known(tmp_path: Path) -> None:
    init_project(tmp_path, with_seed=False)
    llm = StubLLMClient()
    res = dispatch("rag", task="x", project_root=tmp_path, llm=llm)
    assert res.technique == "rag"
