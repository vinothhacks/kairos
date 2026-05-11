"""kairos config loader (KAI-004).

Resolution order: env > .kairos/config.toml > built-in defaults.

Recognized TOML layout:

    [llm]
    backend = "mcp"           # or "stub"
    mcp_url = "http://localhost:8765"
    stub_path = ""            # path to a JSON file of canned stub responses

    [runners]
    max_react_steps = 6
    rag_chunk_size = 30
    rag_top_k = 6

    [lint]
    stale_after_days = 180

    [selector]
    tie_break_threshold = 0.05

Recognized env vars (override file):

    KAIROS_LLM_BACKEND   -> llm.backend
    KAIROS_MCP_URL       -> llm.mcp_url
    KAIROS_STUB_PATH     -> llm.stub_path
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULTS: dict[str, object] = {
    "llm_backend": "mcp",
    "mcp_url": "http://localhost:8765",
    "stub_path": "",
    "max_react_steps": 6,
    "rag_chunk_size": 30,
    "rag_top_k": 6,
    "stale_after_days": 180,
    "tie_break_threshold": 0.05,
}


@dataclass
class KairosConfig:
    """Resolved settings used across the CLI, runners, and lint."""

    llm_backend: str = "mcp"
    mcp_url: str = "http://localhost:8765"
    stub_path: str = ""
    max_react_steps: int = 6
    rag_chunk_size: int = 30
    rag_top_k: int = 6
    stale_after_days: int = 180
    tie_break_threshold: float = 0.05
    config_file: Path | None = None
    sources: dict[str, str] = field(default_factory=dict)


def _from_toml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    flat: dict[str, object] = {}
    llm = data.get("llm", {}) if isinstance(data, dict) else {}
    if isinstance(llm, dict):
        if "backend" in llm:
            flat["llm_backend"] = str(llm["backend"])
        if "mcp_url" in llm:
            flat["mcp_url"] = str(llm["mcp_url"])
        if "stub_path" in llm:
            flat["stub_path"] = str(llm["stub_path"])
    runners = data.get("runners", {}) if isinstance(data, dict) else {}
    if isinstance(runners, dict):
        for key, target in (
            ("max_react_steps", "max_react_steps"),
            ("rag_chunk_size", "rag_chunk_size"),
            ("rag_top_k", "rag_top_k"),
        ):
            if key in runners:
                try:
                    flat[target] = int(runners[key])
                except (TypeError, ValueError):
                    continue
    lint = data.get("lint", {}) if isinstance(data, dict) else {}
    if isinstance(lint, dict) and "stale_after_days" in lint:
        try:
            flat["stale_after_days"] = int(lint["stale_after_days"])
        except (TypeError, ValueError):
            pass
    selector = data.get("selector", {}) if isinstance(data, dict) else {}
    if isinstance(selector, dict) and "tie_break_threshold" in selector:
        try:
            flat["tie_break_threshold"] = float(selector["tie_break_threshold"])
        except (TypeError, ValueError):
            pass
    return flat


def _from_env(env: dict[str, str]) -> dict[str, object]:
    flat: dict[str, object] = {}
    if env.get("KAIROS_LLM_BACKEND"):
        flat["llm_backend"] = env["KAIROS_LLM_BACKEND"]
    if env.get("KAIROS_MCP_URL"):
        flat["mcp_url"] = env["KAIROS_MCP_URL"]
    if env.get("KAIROS_STUB_PATH"):
        flat["stub_path"] = env["KAIROS_STUB_PATH"]
    return flat


def load_config(project_root: Path, *, env: dict[str, str] | None = None) -> KairosConfig:
    """Resolve env > file > defaults into a KairosConfig.

    `project_root` is the kairos project (where `.kairos/config.toml` lives).
    `env` defaults to `os.environ` so callers can stub for tests.
    """
    env_map = dict(os.environ if env is None else env)
    file_path = project_root / ".kairos" / "config.toml"
    file_data = _from_toml(file_path)
    env_data = _from_env(env_map)
    merged: dict[str, object] = {}
    sources: dict[str, str] = {}
    for key, default in _DEFAULTS.items():
        if key in env_data:
            merged[key] = env_data[key]
            sources[key] = "env"
        elif key in file_data:
            merged[key] = file_data[key]
            sources[key] = "file"
        else:
            merged[key] = default
            sources[key] = "default"
    return KairosConfig(
        llm_backend=str(merged["llm_backend"]),
        mcp_url=str(merged["mcp_url"]),
        stub_path=str(merged["stub_path"]),
        max_react_steps=_as_int(merged["max_react_steps"], _DEFAULTS["max_react_steps"]),
        rag_chunk_size=_as_int(merged["rag_chunk_size"], _DEFAULTS["rag_chunk_size"]),
        rag_top_k=_as_int(merged["rag_top_k"], _DEFAULTS["rag_top_k"]),
        stale_after_days=_as_int(merged["stale_after_days"], _DEFAULTS["stale_after_days"]),
        tie_break_threshold=_as_float(
            merged["tie_break_threshold"], _DEFAULTS["tie_break_threshold"]
        ),
        config_file=file_path if file_path.exists() else None,
        sources=sources,
    )


def _as_int(value: object, default: object) -> int:
    if isinstance(value, bool):  # bool is a subclass of int; reject explicitly
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
    return int(default) if isinstance(default, int) else 0


def _as_float(value: object, default: object) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            pass
    return float(default) if isinstance(default, (int, float)) else 0.0


__all__ = ["KairosConfig", "load_config"]
