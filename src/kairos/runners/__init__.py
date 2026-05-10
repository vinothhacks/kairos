"""Runners — implementations of agent techniques.

Each runner is a pure function that takes (task, project_root, llm) and
returns a `RunResult`. The CLI dispatches by name. Adding a new runner is
"register a callable + add a concept page with `has_runner: true`".
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from kairos.llm.mcp_client import LLMClient
from kairos.runners.base import RunResult
from kairos.runners.rag import run_rag
from kairos.runners.react import run_react
from kairos.runners.reflexion import run_reflexion

RunnerFn = Callable[..., RunResult]

REGISTRY: dict[str, RunnerFn] = {
    "rag": run_rag,
    "react": run_react,
    "reflexion": run_reflexion,
}


def dispatch(technique: str, *, task: str, project_root: Path, llm: LLMClient) -> RunResult:
    """Look up a runner by name and execute it. Raises ValueError if unknown."""
    runner = REGISTRY.get(technique.lower())
    if runner is None:
        raise ValueError(f"unknown technique: {technique!r}. Known: {sorted(REGISTRY)}")
    return runner(task=task, project_root=project_root, llm=llm)


__all__ = ["RunResult", "dispatch", "REGISTRY"]
