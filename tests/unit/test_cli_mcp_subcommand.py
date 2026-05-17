"""CLI surface for the kairos MCP server."""
from __future__ import annotations

from typer.testing import CliRunner

from kairos.cli import app


def test_mcp_serve_help_is_available() -> None:
    result = CliRunner().invoke(app, ["mcp", "serve", "--help"])

    assert result.exit_code == 0
    assert "stdio" in result.stdout.lower()
