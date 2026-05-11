"""Runners - implementations of agent techniques.

v0.2 introduces a `Runner` ABC and entry-point plugin discovery (KAI-006).

Two surfaces are exposed for back-compat:

- `REGISTRY`: dict[str, callable] of legacy `run_X` functions (kept for v0.1 callers).
- `RUNNERS`:  dict[str, Runner] of `Runner` instances used by the new dispatch path.

Plugins ship a class subclassing `Runner` and register under the
`kairos.runners` entry-point group. On first dispatch we discover them and
add them to `RUNNERS`.
"""
from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from pathlib import Path

from kairos.llm.mcp_client import LLMClient
from kairos.runners.base import Runner, RunResult
from kairos.runners.rag import RagRunner, run_rag
from kairos.runners.react import ReactRunner, run_react
from kairos.runners.reflexion import ReflexionRunner, run_reflexion

RunnerFn = Callable[..., RunResult]

REGISTRY: dict[str, RunnerFn] = {
    "rag": run_rag,
    "react": run_react,
    "reflexion": run_reflexion,
}

RUNNERS: dict[str, Runner] = {
    "rag": RagRunner(),
    "react": ReactRunner(),
    "reflexion": ReflexionRunner(),
}

_PLUGINS_LOADED = False


def _load_plugins() -> None:
    """Discover Runner subclasses exposed via the `kairos.runners` entry-point group."""
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED:
        return
    _PLUGINS_LOADED = True
    try:
        eps = entry_points(group="kairos.runners")
    except Exception:  # noqa: BLE001 - importlib.metadata can be quirky
        return
    for ep in eps:
        try:
            cls = ep.load()
        except Exception:  # noqa: BLE001
            continue
        try:
            inst = cls() if isinstance(cls, type) else cls
        except Exception:  # noqa: BLE001
            continue
        if isinstance(inst, Runner) and inst.name and inst.name not in RUNNERS:
            RUNNERS[inst.name] = inst


def runner_for(name: str) -> Runner:
    """Look up a Runner instance by name. Raises KeyError if unknown."""
    _load_plugins()
    key = name.lower()
    if key not in RUNNERS:
        raise KeyError(f"unknown technique: {name!r}. Known: {sorted(RUNNERS)}")
    return RUNNERS[key]


def dispatch(
    technique: str,
    *,
    task: str,
    project_root: Path,
    llm: LLMClient,
    selected_by: str = "user",
    selector_score: float | None = None,
    **kwargs: object,
) -> RunResult:
    """Look up a runner and execute it.

    `selected_by` and `selector_score` flow into the run record so auto-
    selected runs are distinguishable from user-pinned ones (KAI-008).
    """
    _load_plugins()
    key = technique.lower()
    inst = RUNNERS.get(key)
    if inst is not None:
        return inst.run(
            task=task,
            project_root=project_root,
            llm=llm,
            selected_by=selected_by,
            selector_score=selector_score,
            **kwargs,
        )
    fn = REGISTRY.get(key)
    if fn is None:
        raise ValueError(
            f"unknown technique: {technique!r}. Known: {sorted(set(RUNNERS) | set(REGISTRY))}"
        )
    return fn(
        task=task,
        project_root=project_root,
        llm=llm,
        selected_by=selected_by,
        selector_score=selector_score,
        **kwargs,
    )


__all__ = [
    "RunResult",
    "Runner",
    "RUNNERS",
    "REGISTRY",
    "dispatch",
    "runner_for",
]
