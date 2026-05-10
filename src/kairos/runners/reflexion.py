"""Reflexion runner — initial answer -> critique -> revised answer.

We split the work across two providers to demonstrate the cross-provider
two-model handoff that's a kairos signature: ChatGPT drafts, Claude critiques,
ChatGPT revises.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from kairos.llm.mcp_client import LLMClient
from kairos.runners.base import RunRecorder, RunResult


def run_reflexion(
    *,
    task: str,
    project_root: Path,
    llm: LLMClient,
) -> RunResult:
    """Two-stage Reflexion (initial -> critique -> revise) using both providers."""
    rec = RunRecorder(project_root=project_root, technique="reflexion", task=task)
    rec.event("reflexion_start")

    # Stage 1: ChatGPT initial answer.
    initial_prompt = dedent(
        f"""
        Answer this task carefully and concisely. We will critique it and
        revise.

        TASK: {task}
        """
    ).strip()
    rec.event("initial_prompt", chars=len(initial_prompt))
    initial = llm.chatgpt_send(initial_prompt).text.strip()
    rec.event("initial_done", reply_chars=len(initial))

    # Stage 2: Claude critique.
    critique_prompt = dedent(
        f"""
        Critique the following answer to a task. Identify factual errors,
        logical gaps, missing caveats, and weak reasoning. Be specific. Then
        list 3 concrete improvements the author should make.

        TASK: {task}

        ANSWER:
        ---
        {initial}
        ---

        Format: 1 paragraph of critique + bulleted improvements.
        """
    ).strip()
    rec.event("critique_prompt", chars=len(critique_prompt))
    critique = llm.claude_send(critique_prompt).text.strip()
    rec.event("critique_done", reply_chars=len(critique))

    # Stage 3: ChatGPT revise.
    revise_prompt = dedent(
        f"""
        You wrote the answer below. Apply the critique to produce a revised
        answer. Keep the parts that are correct. Be concrete.

        TASK: {task}

        YOUR INITIAL ANSWER:
        ---
        {initial}
        ---

        CRITIQUE:
        ---
        {critique}
        ---

        Output ONLY the revised answer, no preamble.
        """
    ).strip()
    rec.event("revise_prompt", chars=len(revise_prompt))
    revised = llm.chatgpt_send(revise_prompt).text.strip()
    rec.event("revise_done", reply_chars=len(revised))

    final = revised or initial or "(reflexion: empty)"
    return rec.finish(answer=final, selected_by="user")
