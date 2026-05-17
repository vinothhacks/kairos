"""ReAct runner - Thought / Action / Observation loop with three tools.

Tools available to the model:
  - search_web(q)     -> claude_search_web (or chatgpt_search_web if you swap)
  - read_file(path)   -> reads a file under project_root
  - finish(answer)    -> ends the loop and returns `answer`

The loop is bounded at `max_steps` (default 6). Output ends when the model
calls finish() or the budget runs out.

The model's reply must follow the structured format below; otherwise we fall
back to treating the whole reply as the final answer.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from kairos.llm.providers import LLMClient
from kairos.runners.base import Runner, RunRecorder, RunResult
from kairos.utils.paths import WikiPaths

_ACTION_RE = re.compile(
    r"(?:^|\n)\s*Action\s*:\s*(?P<tool>\w+)\s*\((?P<arg>.*?)\)\s*(?:\n|$)",
    re.IGNORECASE | re.DOTALL,
)
_FINISH_RE = re.compile(r"(?:^|\n)\s*Final\s*Answer\s*:\s*(?P<answer>.*)$", re.IGNORECASE | re.DOTALL)
_THOUGHT_RE = re.compile(r"(?:^|\n)\s*Thought\s*:\s*(?P<t>.+?)(?:\n|$)", re.IGNORECASE)


@dataclass
class _Step:
    thought: str
    action_tool: str | None
    action_arg: str
    observation: str


def run_react(
    *,
    task: str,
    project_root: Path,
    llm: LLMClient,
    max_steps: int = 6,
    selected_by: str = "user",
    selector_score: float | None = None,
) -> RunResult:
    """Execute a ReAct loop bounded at `max_steps`."""
    paths = WikiPaths(root=project_root)
    rec = RunRecorder(project_root=project_root, technique="react", task=task)
    rec.event("react_start", max_steps=max_steps)

    history: list[_Step] = []

    final_answer: str | None = None
    for step in range(max_steps):
        prompt = _build_prompt(task=task, history=history, project_root=project_root)
        rec.event("step_prompt", step=step, prompt_chars=len(prompt))
        reply = llm.claude_send(prompt).text
        rec.event("step_reply", step=step, reply_chars=len(reply))

        # Was a finish requested?
        m_finish = _FINISH_RE.search(reply)
        if m_finish:
            final_answer = m_finish.group("answer").strip()
            rec.event("step_finish", step=step)
            break

        m_thought = _THOUGHT_RE.search(reply)
        thought = m_thought.group("t").strip() if m_thought else "(no thought)"

        m_action = _ACTION_RE.search(reply)
        if not m_action:
            # No structured action and no finish -> treat reply as final answer.
            final_answer = reply.strip()
            rec.event("step_unstructured", step=step)
            break

        tool = m_action.group("tool").strip().lower()
        arg = m_action.group("arg").strip().strip("\"'")

        observation = _execute_tool(tool=tool, arg=arg, llm=llm, project_root=paths.root)
        rec.event("step_obs", step=step, tool=tool, arg=arg[:100], obs_chars=len(observation))
        history.append(_Step(thought=thought, action_tool=tool, action_arg=arg, observation=observation))

    if final_answer is None:
        final_answer = "(react: max steps reached without a final answer)"

    return rec.finish(answer=final_answer, selected_by=selected_by, selector_score=selector_score)


class ReactRunner(Runner):
    """KAI-006: object form of run_react for plugin discovery + dispatch ABC."""

    name = "react"

    def applicable(self, task: str) -> bool:  # noqa: D401
        return True

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
        return run_react(
            task=task,
            project_root=project_root,
            llm=llm,
            selected_by=selected_by,
            selector_score=selector_score,
            **kwargs,  # type: ignore[arg-type]
        )


def _build_prompt(*, task: str, history: list[_Step], project_root: Path) -> str:
    history_blocks = []
    for i, step in enumerate(history, 1):
        history_blocks.append(
            dedent(
                f"""
                Step {i}:
                Thought: {step.thought}
                Action: {step.action_tool}({json.dumps(step.action_arg)})
                Observation: {step.observation[:1500]}
                """
            ).strip()
        )
    history_text = "\n\n".join(history_blocks) or "(no steps yet)"
    return dedent(
        f"""
        You are running a ReAct loop. Available tools:
          - search_web(q)        : run a web search and return a summary
          - read_file(path)      : read a file from the project (rooted at {project_root})
          - finish(answer)       : provide the final answer

        Output strictly one of:
          Thought: <your reasoning>
          Action: <tool>(<arg>)
        OR
          Final Answer: <answer>

        TASK: {task}

        HISTORY SO FAR:
        {history_text}
        """
    ).strip()


def _execute_tool(*, tool: str, arg: str, llm: LLMClient, project_root: Path) -> str:
    tool = tool.lower()
    if tool == "search_web":
        return llm.search_web(arg, provider="claude").text[:1500]
    if tool == "read_file":
        target = (project_root / arg).resolve()
        try:
            target.relative_to(project_root.resolve())
        except ValueError:
            return f"(read_file: refused, path escapes project root: {arg})"
        if not target.exists():
            return f"(read_file: not found: {arg})"
        try:
            return target.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError as e:
            return f"(read_file: io error: {e})"
    if tool == "finish":
        return arg
    return f"(unknown tool: {tool!r})"
