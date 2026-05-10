"""Wiki page schema + frontmatter parsing.

Implements the contract defined in AGENTS.md:
- YAML frontmatter delimited by '---'
- Required keys: title, type, created, updated, confidence
- Optional keys: sources, related, has_runner

Also exposes a tiny helper to validate that a project's AGENTS.md exists.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

PageType = Literal["concept", "source", "comparison"]
Confidence = Literal["high", "medium", "low"]

_FRONT_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n(.*)$", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]")


@dataclass
class PageFrontmatter:
    """Strict view of a wiki page's frontmatter."""

    title: str
    type: PageType
    created: _dt.date
    updated: _dt.date
    confidence: Confidence = "medium"
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    has_runner: bool = False
    extra: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> PageFrontmatter:
        if not isinstance(raw, dict):
            raise ValueError("frontmatter must be a mapping")
        required = {"title", "type", "created", "updated"}
        missing = required - raw.keys()
        if missing:
            raise ValueError(f"frontmatter missing required keys: {sorted(missing)}")

        page_type = str(raw["type"])
        if page_type not in {"concept", "source", "comparison"}:
            raise ValueError(f"invalid page type: {page_type!r}")

        confidence = str(raw.get("confidence", "medium"))
        if confidence not in {"high", "medium", "low"}:
            raise ValueError(f"invalid confidence: {confidence!r}")

        sources_raw = raw.get("sources") or []
        related_raw = raw.get("related") or []
        if not isinstance(sources_raw, list):
            sources_raw = []
        if not isinstance(related_raw, list):
            related_raw = []

        return cls(
            title=str(raw["title"]),
            type=page_type,  # type: ignore[arg-type]
            created=_to_date(raw["created"]),
            updated=_to_date(raw["updated"]),
            confidence=confidence,  # type: ignore[arg-type]
            sources=[str(s) for s in sources_raw],
            related=[str(s) for s in related_raw],
            has_runner=bool(raw.get("has_runner", False)),
            extra={
                k: v
                for k, v in raw.items()
                if k
                not in {
                    "title",
                    "type",
                    "created",
                    "updated",
                    "confidence",
                    "sources",
                    "related",
                    "has_runner",
                }
            },
        )

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "title": self.title,
            "type": self.type,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "confidence": self.confidence,
        }
        if self.sources:
            out["sources"] = list(self.sources)
        if self.related:
            out["related"] = list(self.related)
        if self.has_runner:
            out["has_runner"] = True
        out.update(self.extra)
        return out


def _to_date(v: object) -> _dt.date:
    if isinstance(v, _dt.date) and not isinstance(v, _dt.datetime):
        return v
    if isinstance(v, _dt.datetime):
        return v.date()
    return _dt.date.fromisoformat(str(v))


def parse_page(text: str) -> tuple[PageFrontmatter, str]:
    """Split a markdown page into (frontmatter, body). Raises ValueError on bad pages."""
    match = _FRONT_RE.match(text)
    if not match:
        raise ValueError("page is missing YAML frontmatter")
    raw = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).lstrip("\n")
    return PageFrontmatter.from_dict(raw), body


def render_frontmatter(fm: PageFrontmatter) -> str:
    """Serialize frontmatter to a YAML block (trailing newline included)."""
    body = yaml.safe_dump(fm.to_dict(), sort_keys=False, allow_unicode=True).strip()
    return f"---\n{body}\n---\n"


def render_page(fm: PageFrontmatter, body: str) -> str:
    """Serialize frontmatter + body back into a single markdown string."""
    body_clean = body.lstrip("\n")
    if not body_clean.endswith("\n"):
        body_clean += "\n"
    return render_frontmatter(fm) + "\n" + body_clean


def extract_wikilinks(text: str) -> list[str]:
    """Pull all [[wikilink]] targets from a body. De-duped, order-preserving."""
    seen: list[str] = []
    for match in _WIKILINK_RE.finditer(text):
        target = match.group(1).strip()
        if target and target not in seen:
            seen.append(target)
    return seen


def validate_schema_loaded(root: Path) -> None:
    """Hard-fail if the project root does not have a valid AGENTS.md."""
    schema = root / "AGENTS.md"
    if not schema.exists():
        raise FileNotFoundError(
            f"AGENTS.md not found at {schema}. Run `kairos init` first."
        )
    text = schema.read_text(encoding="utf-8")
    if "Project structure" not in text or "## Workflows" not in text:
        raise ValueError(
            f"AGENTS.md at {schema} is missing required sections. "
            f"Run `kairos init --force` to refresh from the seed schema."
        )
