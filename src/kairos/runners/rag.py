"""RAG runner - retrieval augmented generation over a folder.

v0.1 retrieval is lexical:
  - chunk every .md file under raw/ at ~chunk_size lines
  - score chunks by token overlap with the task
  - take top-k chunks, build context, single chatgpt_send call

This stays purely local-friendly; no embeddings required.
"""
from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from kairos.llm.providers import LLMClient
from kairos.runners.base import Runner, RunRecorder, RunResult
from kairos.utils.paths import WikiPaths

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]+")
_STOPWORDS = frozenset({"the", "a", "an", "and", "or", "of", "is", "to", "for", "in", "on", "with", "by"})

# KAI-044: skip pathological inputs so a single 50MB markdown dump can't OOM
# the runner. 5MB matches the audit recommendation.
_MAX_RAG_FILE_BYTES = 5 * 1024 * 1024


@dataclass
class _Chunk:
    file: Path
    start_line: int
    end_line: int
    text: str


def run_rag(
    *,
    task: str,
    project_root: Path,
    llm: LLMClient,
    source_folder: Path | None = None,
    chunk_size: int = 30,
    top_k: int = 6,
    selected_by: str = "user",
    selector_score: float | None = None,
) -> RunResult:
    """Answer `task` using retrieval over markdown files in `source_folder` (defaults to raw/)."""
    paths = WikiPaths(root=project_root)
    folder = source_folder or paths.raw
    rec = RunRecorder(project_root=project_root, technique="rag", task=task)
    rec.event("retrieval_start", folder=str(folder), chunk_size=chunk_size, top_k=top_k)

    chunks = list(_chunk_folder(folder, chunk_size=chunk_size))
    rec.event("chunks_built", count=len(chunks))

    q_tokens = _tokenize(task)
    scored = sorted(
        (
            (
                _score(q_tokens, _tokenize(c.text)),
                c,
            )
            for c in chunks
        ),
        key=lambda x: x[0],
        reverse=True,
    )
    top = [c for s, c in scored[:top_k] if s > 0]
    rec.event("retrieval_top_k", picked=len(top))

    context_blocks = []
    for c in top:
        rel = c.file.relative_to(project_root) if c.file.is_relative_to(project_root) else c.file
        context_blocks.append(f"--- {rel.as_posix()} L{c.start_line}-L{c.end_line} ---\n{c.text}")
    context = "\n\n".join(context_blocks) if context_blocks else "(no relevant context found in raw/)"

    prompt = dedent(
        f"""
        Answer the user's task using ONLY the context provided. Cite chunks
        like (source: <file> Lstart-Lend). If the context is insufficient,
        say so explicitly.

        TASK:
        {task}

        CONTEXT (top-{len(top)} retrieved chunks):
        {context[:14000]}

        Format: 1-3 paragraphs followed by a "Sources" bulleted list.
        """
    ).strip()

    rec.event("llm_call", tool="chatgpt_send", prompt_chars=len(prompt))
    answer = llm.chatgpt_send(prompt).text.strip()
    rec.event("llm_done", reply_chars=len(answer))

    return rec.finish(
        answer=answer or "(empty answer)",
        selected_by=selected_by,
        selector_score=selector_score,
    )


class RagRunner(Runner):
    """KAI-006: object form of run_rag for plugin discovery + dispatch ABC."""

    name = "rag"

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
        return run_rag(
            task=task,
            project_root=project_root,
            llm=llm,
            selected_by=selected_by,
            selector_score=selector_score,
            **kwargs,  # type: ignore[arg-type]
        )


def _chunk_folder(folder: Path, *, chunk_size: int) -> Iterable[_Chunk]:
    if not folder.exists():
        return
    for path in folder.rglob("*.md"):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > _MAX_RAG_FILE_BYTES:
            # KAI-044: skip oversize files but tell the user, otherwise the
            # missing chunks look like a relevance bug.
            print(
                f"[rag] skipping {path.name} ({size / (1024 * 1024):.1f}MB > 5MB cap)",
                file=sys.stderr,
            )
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()
        for start in range(0, len(lines), chunk_size):
            chunk_lines = lines[start : start + chunk_size]
            chunk_text = "\n".join(chunk_lines).strip()
            if not chunk_text:
                continue
            yield _Chunk(
                file=path,
                start_line=start + 1,
                end_line=start + len(chunk_lines),
                text=chunk_text,
            )


def _tokenize(text: str) -> set[str]:
    return {t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS}


def _score(q: set[str], doc: set[str]) -> float:
    if not q:
        return 0.0
    return float(len(q & doc)) / float(len(q))
