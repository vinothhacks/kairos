"""kairos config loader (KAI-004).

Resolution order: env > .kairos/config.toml > built-in defaults.

Recognized TOML layout:

    [llm]
    backend = "stub"          # stub, ollama, openai, anthropic, openai_compat
    stub_path = ""            # path to a JSON file of canned stub responses

    [runners]
    max_react_steps = 6
    rag_chunk_size = 30
    rag_top_k = 6

    [lint]
    stale_after_days = 180

    [selector]
    tie_break_threshold = 0.05
    default_technique = "rag"
    require_runner = true

    [sources]
    my_docs = "./raw"

Recognized env vars (override file):

    KAIROS_LLM_BACKEND   -> llm.backend
    KAIROS_STUB_PATH     -> llm.stub_path
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULTS: dict[str, object] = {
    "llm_backend": "stub",
    "mcp_url": "",
    "stub_path": "",
    "max_react_steps": 6,
    "rag_chunk_size": 30,
    "rag_top_k": 6,
    "stale_after_days": 180,
    "auto_save_query_answers": False,
    "tie_break_threshold": 0.05,
    "default_technique": "rag",
    "require_runner": True,
    "source_paths": {},
}


@dataclass
class KairosConfig:
    """Resolved settings used across the CLI, runners, and lint."""

    llm_backend: str = "stub"
    mcp_url: str = ""
    stub_path: str = ""
    max_react_steps: int = 6
    rag_chunk_size: int = 30
    rag_top_k: int = 6
    stale_after_days: int = 180
    auto_save_query_answers: bool = False
    tie_break_threshold: float = 0.05
    default_technique: str = "rag"
    require_runner: bool = True
    source_paths: dict[str, str] = field(default_factory=dict)
    config_had_bom: bool = False
    config_file: Path | None = None
    sources: dict[str, str] = field(default_factory=dict)


def _from_toml(path: Path) -> dict[str, object]:  # noqa: C901
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8-sig")
        data = tomllib.loads(text)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    flat: dict[str, object] = {}
    if path.read_bytes().startswith(b"\xef\xbb\xbf"):
        flat["config_had_bom"] = True
    llm = data.get("llm", {}) if isinstance(data, dict) else {}
    if isinstance(llm, dict):
        if "backend" in llm:
            backend = str(llm["backend"])
            flat["llm_backend"] = backend.lower().strip()
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
    wiki = data.get("wiki", {}) if isinstance(data, dict) else {}
    if isinstance(wiki, dict):
        if "stale_after_days" in wiki:
            try:
                flat["stale_after_days"] = int(wiki["stale_after_days"])
            except (TypeError, ValueError):
                pass
        if "auto_save_query_answers" in wiki:
            flat["auto_save_query_answers"] = _as_bool(wiki["auto_save_query_answers"])
    lint = data.get("lint", {}) if isinstance(data, dict) else {}
    if isinstance(lint, dict) and "stale_after_days" in lint:
        try:
            flat["stale_after_days"] = int(lint["stale_after_days"])
        except (TypeError, ValueError):
            pass
    selector = data.get("selector", {}) if isinstance(data, dict) else {}
    if isinstance(selector, dict):
        if "tie_break_threshold" in selector:
            try:
                flat["tie_break_threshold"] = float(selector["tie_break_threshold"])
            except (TypeError, ValueError):
                pass
        if "default_technique" in selector:
            flat["default_technique"] = str(selector["default_technique"]).lower().strip()
        if "require_runner" in selector:
            flat["require_runner"] = _as_bool(selector["require_runner"])
    sources_block = data.get("sources", {}) if isinstance(data, dict) else {}
    if isinstance(sources_block, dict):
        flat["source_paths"] = {str(k): str(v) for k, v in sources_block.items()}
    return flat


def _from_env(env: dict[str, str]) -> dict[str, object]:
    flat: dict[str, object] = {}
    if env.get("KAIROS_LLM_BACKEND"):
        backend = env["KAIROS_LLM_BACKEND"]
        flat["llm_backend"] = backend.lower().strip()
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
        auto_save_query_answers=_as_bool(merged["auto_save_query_answers"]),
        tie_break_threshold=_as_float(
            merged["tie_break_threshold"], _DEFAULTS["tie_break_threshold"]
        ),
        default_technique=str(merged["default_technique"]).lower().strip() or "rag",
        require_runner=_as_bool(merged["require_runner"]),
        source_paths=dict(merged["source_paths"]) if isinstance(merged["source_paths"], dict) else {},
        config_had_bom=_as_bool(file_data.get("config_had_bom", False)),
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


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


__all__ = ["KairosConfig", "load_config"]
