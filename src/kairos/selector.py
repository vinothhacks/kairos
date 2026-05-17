"""Technique selector - given a task, rank wiki concept pages.

v0.1 selector is rule-based and runs without network. The headline rules:

1. Tag-based shortcuts - keywords in the task map to a technique.
   ('search', 'browse', 'web' -> react)
   ('critique', 'verify', 'check', 'self-correct' -> reflexion)
   ('summarize', 'document', 'explain' -> rag)
2. Lexical overlap - task tokens vs concept-page summary tokens.
3. has_runner gating - concept pages without a runner cannot win unless the
   user explicitly passed `--technique <name>`.
4. Tie-break - prefer 'rag' (the safe default) when scores are within 0.05.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from kairos.llm.providers import LLMClient
from kairos.memory.wiki_index import WikiIndexer
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
    tie_break_threshold: float = 0.05,
    default_technique: str = DEFAULT_TECHNIQUE,
) -> list[TechniqueChoice]:
    """Rank techniques against the task. Returns top-N (always at least 1).

    KAI-021: when the wiki_index cache is populated and fresh, use it to
    enumerate has_runner concept pages without parsing every page on disk.
    Falls back to a filesystem scan whenever the cache is empty or stale.
    """
    paths = WikiPaths(root=project_root)
    tokens = _tokenize(task)

    candidate_paths = _enumerate_concept_paths(paths=paths, require_runner=require_runner)
    candidates: list[TechniqueChoice] = []
    for path in candidate_paths:
        try:
            fm, body = parse_page(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            # KAI-033: surface skipped pages as a stderr warning so a malformed
            # wiki does not silently shrink the candidate set.
            print(f"[selector] skipping malformed page {path}: {e}", file=sys.stderr)
            continue
        slug = path.stem
        if require_runner and not fm.has_runner:
            continue

        body_tokens = _tokenize(body)
        overlap = len(tokens & body_tokens)
        # KAI-028: segment match instead of substring; "rag" should not also
        # match "rage" or "ragdoll" or "garage".
        slug_segments = set(slug.split("-"))
        slug_match = sum(1 for t in tokens if t in slug_segments)
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
                technique=default_technique,
                score=0.0,
                rationale="fallback: no eligible technique pages found",
                page=None,
            )
        ]

    candidates.sort(key=lambda c: c.score, reverse=True)

    # KAI-029: tie-break across the top-N (default top-3). If any candidate
    # within 0.05 of the leader is the safe default, promote it. Previously
    # this only inspected top-1 vs top-2, so a 3-way near-tie could still
    # pick a non-default winner.
    if len(candidates) >= 2:
        top = candidates[0]
        for i in range(1, min(3, len(candidates))):
            cand = candidates[i]
            if abs(top.score - cand.score) < tie_break_threshold and cand.technique == default_technique:
                candidates[0], candidates[i] = cand, top
                candidates[0].rationale += " | tie-break preferred default"
                break

    return candidates


def _tokenize(text: str) -> set[str]:
    return {t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS}


def _enumerate_concept_paths(*, paths: WikiPaths, require_runner: bool) -> list[Path]:
    """KAI-021: prefer the wiki_index cache, fall back to a filesystem scan.

    Strategy:
      1. If the cache has any concept rows, use it.
      2. For each cached row, the file must still exist on disk; if its mtime
         is newer than `last_seen_ts`, the cache row is stale -> include the
         path anyway and let the caller re-parse from disk.
      3. Add any on-disk concept paths the cache has not seen yet (newly
         created pages, copied seed wiki, etc).
      4. If the cache is completely empty, fall back to the legacy FS scan
         (pure glob over `paths.concepts`).
    """
    fs_paths = sorted(paths.concepts.glob("*.md"))
    try:
        idx = WikiIndexer(db_path=paths.db)
        rows = idx.all_pages(kind="concept")
    except Exception:  # noqa: BLE001
        # If the SQLite cache itself is unhealthy, fall back hard. The CLI's
        # `kairos doctor` is the right surface to flag this.
        return fs_paths
    if not rows:
        return fs_paths

    cached_paths: list[Path] = []
    seen_files: set[str] = set()
    for row in rows:
        has_runner_raw = row.get("has_runner")
        has_runner = bool(has_runner_raw) if has_runner_raw is not None else False
        if require_runner and not has_runner:
            seen_files.add(str(row.get("file") or ""))
            continue
        file_rel = row.get("file")
        if not isinstance(file_rel, str) or not file_rel:
            continue
        path = paths.root / file_rel
        seen_files.add(file_rel)
        if path.exists():
            cached_paths.append(path)

    # Pages on disk that the cache hasn't observed yet still need to be ranked.
    for fs_path in fs_paths:
        rel = fs_path.relative_to(paths.root).as_posix()
        if rel not in seen_files:
            cached_paths.append(fs_path)

    return sorted(set(cached_paths))
