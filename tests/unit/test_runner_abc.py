"""KAI-006 regression tests: Runner ABC + entry_points plugin discovery."""
from __future__ import annotations

from pathlib import Path

import pytest

from kairos.llm.mcp_client import StubLLMClient
from kairos.runners import REGISTRY, RUNNERS, Runner, dispatch, runner_for
from kairos.runners.base import RunResult


def test_runner_abc_is_abstract() -> None:
    """Runner can't be instantiated without implementing applicable()/run()."""
    with pytest.raises(TypeError):
        Runner()  # type: ignore[abstract]


def test_builtin_runners_registered() -> None:
    """The three built-in runners must be registered as Runner instances."""
    assert {"rag", "react", "reflexion"}.issubset(set(RUNNERS.keys()))
    for name in ("rag", "react", "reflexion"):
        assert isinstance(RUNNERS[name], Runner), f"{name} runner is not a Runner subclass instance"


def test_runner_for_returns_correct_instance() -> None:
    runner = runner_for("rag")
    assert isinstance(runner, Runner)
    assert runner.name == "rag"


def test_runner_applicable_is_callable() -> None:
    for name in ("rag", "react", "reflexion"):
        runner = runner_for(name)
        result = runner.applicable("any task here")
        assert isinstance(result, bool)


def test_dispatch_uses_runner_abc(tmp_path: Path) -> None:
    """dispatch() goes through the Runner ABC, not the legacy callable, by default."""
    from kairos.wiki.init import init_project

    init_project(tmp_path, with_seed=False)
    llm = StubLLMClient()
    res = dispatch("rag", task="anything", project_root=tmp_path, llm=llm)
    assert isinstance(res, RunResult)
    assert res.technique == "rag"


def test_legacy_registry_still_works() -> None:
    """Back-compat: REGISTRY is still a dict[str, callable] for v0.1 callers."""
    assert callable(REGISTRY["rag"])
    assert callable(REGISTRY["react"])
    assert callable(REGISTRY["reflexion"])
