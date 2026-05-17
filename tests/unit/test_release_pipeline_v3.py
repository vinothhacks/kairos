"""KAI3 release-pipeline and installer regression tests."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SHA_RE = re.compile(r"^[a-f0-9]{40}$")


def _load_yaml(path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _collect_uses(node: object) -> list[str]:
    refs: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                refs.append(value)
            else:
                refs.extend(_collect_uses(value))
    elif isinstance(node, list):
        for value in node:
            refs.extend(_collect_uses(value))
    return refs


def test_third_party_github_actions_are_sha_pinned() -> None:
    """KAI3-001: release/CI action refs must be immutable 40-char SHAs."""
    workflow_paths = [
        ".github/workflows/release.yml",
        ".github/workflows/ci.yml",
        ".github/actions/setup-kairos/action.yml",
    ]
    refs = []
    for path in workflow_paths:
        refs.extend(_collect_uses(_load_yaml(path)))

    third_party = sorted({ref for ref in refs if "@" in ref and not ref.startswith("./")})
    floating = [ref for ref in third_party if not SHA_RE.fullmatch(ref.rsplit("@", 1)[1])]

    assert third_party, "expected to audit at least one third-party action"
    assert floating == []


def test_release_write_permissions_are_publish_job_only() -> None:
    """KAI3-002: test/lint jobs must not inherit contents:write or id-token:write."""
    release = _load_yaml(".github/workflows/release.yml")

    assert release.get("permissions") in ({}, None)

    jobs = release["jobs"]
    assert jobs["test"]["permissions"] == {"contents": "read"}
    assert jobs["lint"]["permissions"] == {"contents": "read"}
    assert jobs["build-and-publish"]["permissions"] == {
        "contents": "write",
        "id-token": "write",
    }


def test_release_checks_tag_matches_project_versions_before_build() -> None:
    """KAI3-003: tag, pyproject.toml, and __version__ must agree before publish."""
    release_text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    verify_pos = release_text.index("Verify tag matches package version")
    build_pos = release_text.index("Build sdist + wheel")
    assert verify_pos < build_pos
    assert "github.ref_name" in release_text
    assert "pyproject.toml" in release_text
    assert "src/kairos/__init__.py" in release_text
    assert "__version__" in release_text


def test_installers_pin_default_package_version_and_allow_override() -> None:
    """KAI3-004: one-liners should install a known package version by default."""
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "kairos-agent==$Version" in ps1
    assert "param(" in ps1 and "$Version = '0.4.0'" in ps1
    assert "kairos-agent==$VERSION" in sh
    assert 'VERSION="${KAIROS_VERSION:-0.4.0}"' in sh


def test_powershell_installer_does_not_stop_on_benign_stderr() -> None:
    """KAI3-005: uv stderr must not be promoted to a false NativeCommandError."""
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "$ErrorActionPreference = 'Stop'" not in ps1
    assert "2>&1 | ForEach-Object { Write-Host $_ }" in ps1
    assert "$LASTEXITCODE" in ps1


def test_ci_requires_v04_audit_and_mcp_gates() -> None:
    """v0.4: issue-1 NOT RUN gaps must stay wired into CI."""
    ci_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "uv run bandit -ll -r src/" in ci_text
    assert "uv run pip-audit --strict" in ci_text
    assert "uv run radon cc -a src/" in ci_text
    assert "semgrep --config p/python --config p/security-audit --error src/" in ci_text
    assert "live-ollama" in ci_text
    assert "KAIROS_LIVE=ollama" in ci_text
    assert "mcp-smoke" in ci_text
    assert "tests/integration/test_mcp_server.py" in ci_text
    assert "tests/regression/v2/v2_verification.py" in ci_text
    assert "v2-regression-report" in ci_text
    assert "|| true" not in ci_text
