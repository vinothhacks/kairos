"""Shared types + helpers for runners."""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from kairos.llm.mcp_client import LLMClient
from kairos.memory.db import Database
from kairos.utils.paths import WikiPaths


@dataclass
class TraceEvent:
    """One event in a runner's execution trace.

    KAI-042: ts_ms is a float so we keep sub-millisecond precision in fast
    runs (the v0.1 int cast lost up to 1ms per event).
    """

    ts_ms: float
    kind: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass
class RunResult:
    """What a runner produces.

    KAI-034: trace lives at `trace_path` on disk, not on this object. Callers
    that want the full event stream read the JSONL file (or pass
    `kairos run --json`, which inlines it).
    """

    technique: str
    task: str
    answer: str
    status: str = "ok"
    duration_ms: float = 0.0
    run_id: int | None = None
    answer_path: Path | None = None
    trace_path: Path | None = None
    error: str | None = None


class RunRecorder:
    """Helper to record a run's trace + persist to outputs/run-<id>/ + db."""

    def __init__(self, *, project_root: Path, technique: str, task: str) -> None:
        self.paths = WikiPaths(root=project_root)
        self.technique = technique
        self.task = task
        self.start = time.perf_counter()
        self.events: list[TraceEvent] = []

    def event(self, kind: str, **payload: object) -> None:
        # KAI-042: store true elapsed milliseconds, not coerced int.
        elapsed_ms = (time.perf_counter() - self.start) * 1000.0
        self.events.append(TraceEvent(ts_ms=elapsed_ms, kind=kind, payload=payload))

    def finish(
        self,
        *,
        answer: str,
        status: str = "ok",
        error: str | None = None,
        selected_by: str = "selector",
        selector_score: float | None = None,
    ) -> RunResult:
        duration_ms = (time.perf_counter() - self.start) * 1000.0
        db = Database(path=self.paths.db)
        # We need the run id BEFORE writing the trace (to name the folder).
        # SQLite assigns the id on insert; we then create folder and overwrite paths.
        run_id = db.insert_run(
            task=self.task,
            technique=self.technique,
            selected_by=selected_by,
            selector_score=selector_score,
            status=status,
            duration_ms=duration_ms,
            cost_tokens=None,
            answer_path=None,
            trace_path=None,
            error_msg=error,
        )
        run_dir = self.paths.outputs / f"run-{run_id:05d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        answer_path = run_dir / "answer.md"
        trace_path = run_dir / "trace.jsonl"
        answer_path.write_text(answer + ("\n" if not answer.endswith("\n") else ""), encoding="utf-8")
        with trace_path.open("w", encoding="utf-8") as f:
            for ev in self.events:
                f.write(json.dumps({"ts_ms": ev.ts_ms, "kind": ev.kind, **ev.payload}) + "\n")
        # Update the db row with the file paths.
        with db.conn() as c:
            c.execute(
                "UPDATE runs SET answer_path = ?, trace_path = ? WHERE id = ?",
                (
                    answer_path.relative_to(self.paths.root).as_posix(),
                    trace_path.relative_to(self.paths.root).as_posix(),
                    run_id,
                ),
            )
        return RunResult(
            technique=self.technique,
            task=self.task,
            answer=answer,
            status=status,
            duration_ms=duration_ms,
            run_id=run_id,
            answer_path=answer_path,
            trace_path=trace_path,
            error=error,
        )


class Runner(ABC):
    """Abstract base for kairos technique runners (KAI-006).

    Plugins should subclass `Runner`, provide a unique `name`, and register
    themselves under the `kairos.runners` entry-point group.
    """

    name: str = ""

    @abstractmethod
    def applicable(self, task: str) -> bool:
        """Return True when this runner is plausible for `task`.

        v0.1 implementations should always return True; the rule-based selector
        does the real ranking. Plugins can use this to opt out of consideration
        for tasks they cannot handle (e.g. non-English).
        """

    @abstractmethod
    def run(
        self,
        *,
        task: str,
        project_root: Path,
        llm: LLMClient,
        selected_by: str = "user",
        selector_score: float | None = None,
        **kwargs: object,
    ) -> RunResult:
        """Execute the runner. Always returns a RunResult."""


__all__ = ["TraceEvent", "RunResult", "RunRecorder", "Runner"]
