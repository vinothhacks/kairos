"""Technique selector — given a task, rank wiki concept pages.

v0.1 selector is rule-based and runs without network. The headline rules:

1. Tag-based shortcuts — keywords in the task map to a technique.
   ('search', 'browse', 'web' -> react)
   ('critique', 'verify', 'check', 'self-correct' -> reflexion)
   ('summarize', 'document', 'explain' -> rag)
2. Lexical overlap — task tokens vs concept-page summary tokens.
3. has_runner gating — concept pages without a runner cannot win unless the
   user explicitly passed `--technique <name>`.
4. Tie-break — prefer 'rag' (the safe default) when scores are within 0.05.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kairos.llm.mcp_client import LLMClient
from kairos.utils.paths import WikiPaths
from kairos.wiki.schema import parse_page

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]+")
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "is", "to", "for", "in", "on",
        "what", "how", "why", "when", "where", "do", "does", "did", "which",
        "should", "would", "could", "with", "from", "by", "be", "are", "this",
    }
)

KEYWORD_BOOSTS: dict[str, dict[str, float]] = {
    "react": {
        "search": 0.5, "web": 0.5, "browse": 0.5, "lookup": 0.4, "find": 0.3,
        "tool": 0.4, "tools": 0.4, "shell": 0.3, "execute": 0.3,
        "step": 0.2, "steps": 0.2, "investigate": 0.4, "trace": 0.3,
    },
    "reflexion": {
        "critique": 0.6, "self-correct": 0.6, "verify": 0.4, "check": 0.3,
        "review": 0.3, "improve": 0.3, "iterate": 0.3, "refine": 0.4,
        "correct": 0.4, "double-check": 0.6, "polish": 0.3, "validate": 0.4,
    },
    "rag": {
        "summarize": 0.5, "summary": 0.4, "document": 0.4, "explain": 0.3,
        "describe": 0.3, "what": 0.2, "answer": 0.3, "from": 0.1,
        "based": 0.2, "according": 0.3, "cite": 0.4, "citation": 0.4,
        "notes": 0.3, "papers": 0.4, "reading": 0.3,
    },
}

DEFAULT_TECHNIQUE = "rag"


@dataclass
class TechniqueChoice:
    """One ranked technique with its score and a short rationale."""

    technique: str
    score: float
    rationale: str
    page: Path | None = None


def select_technique(
    *,
    task: str,
    project_root: Path,
    llm: LLMClient | None = None,
    require_runner: bool = True,
) -> list[TechniqueChoice]:
    """Rank techniques against the task. Returns top-N (always at least 1)."""
    paths = WikiPaths(root=project_root)
    tokens = _tokenize(task)

    candidates: list[TechniqueChoice] = []
    for path in sorted(paths.concepts.glob("*.md")):
        try:
            fm, body = parse_page(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        slug = path.stem
        if require_runner and not fm.has_runner:
            continue

        body_tokens = _tokenize(body)
        overlap = len(tokens & body_tokens)
        slug_match = sum(1 for t in tokens if t in slug)
        keyword_score = sum(KEYWORD_BOOSTS.get(slug, {}).get(t, 0.0) for t in tokens)
        score = 0.05 * overlap + 0.5 * slug_match + keyword_score

        rationale_bits = []
        if keyword_score > 0:
            rationale_bits.append(f"keyword boost {keyword_score:.2f}")
        if slug_match:
            rationale_bits.append(f"slug match x{slug_match}")
        if overlap:
            rationale_bits.append(f"body overlap x{overlap}")
        rationale = ", ".join(rationale_bits) or "baseline"

        candidates.append(TechniqueChoice(technique=slug, score=score, rationale=rationale, page=path))

    if not candidates:
        # The wiki has no concept pages with runners. Fall back to default.
        return [
            TechniqueChoice(
                technique=DEFAULT_TECHNIQUE,
                score=0.0,
                rationale="fallback: no eligible technique pages found",
                page=None,
            )
        ]

    candidates.sort(key=lambda c: c.score, reverse=True)

    # Tie-break: when top-1 and top-2 within 0.05, prefer 'rag'.
    if len(candidates) >= 2:
        top, runner_up = candidates[0], candidates[1]
        if abs(top.score - runner_up.score) < 0.05 and runner_up.technique == DEFAULT_TECHNIQUE:
            candidates[0], candidates[1] = runner_up, top
            candidates[0].rationale += " | tie-break preferred default"

    return candidates


def _tokenize(text: str) -> set[str]:
    return {t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS}
