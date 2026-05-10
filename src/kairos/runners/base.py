"""Shared types + helpers for runners."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from kairos.memory.db import Database
from kairos.utils.paths import WikiPaths


@dataclass
class TraceEvent:
    """One event in a runner's execution trace."""

    ts_ms: int
    kind: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass
class RunResult:
    """What a runner produces."""

    technique: str
    task: str
    answer: str
    status: str = "ok"
    duration_ms: int = 0
    run_id: int | None = None
    answer_path: Path | None = None
    trace_path: Path | None = None
    trace: list[TraceEvent] = field(default_factory=list)
    error: str | None = None


class RunRecorder:
    """Helper to record a run's trace + persist to outputs/run-<id>/ + db."""

    def __init__(self, *, project_root: Path, technique: str, task: str) -> None:
        self.paths = WikiPaths(root=project_root)
        self.technique = technique
        self.task = task
        self.start = time.monotonic()
        self.events: list[TraceEvent] = []

    def event(self, kind: str, **payload: object) -> None:
        elapsed_ms = int((time.monotonic() - self.start) * 1000)
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
        duration_ms = int((time.monotonic() - self.start) * 1000)
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
            trace=list(self.events),
            error=error,
        )
