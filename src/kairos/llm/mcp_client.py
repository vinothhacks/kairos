"""Compatibility exports for the pre-v0.4 llm-mcp module path.

Kairos v0.4 removed the llm-mcp HTTP shim. New code should import from
`kairos.llm.providers`; this module remains for one release so existing imports
of `LLMClient`, `LLMError`, `LLMResult`, `MCPUnreachable`, and `StubLLMClient`
keep working.
"""
from __future__ import annotations

import warnings

from kairos.llm.providers.base import LLMClient, LLMError, LLMResult, MCPUnreachable
from kairos.llm.providers.stub import StubLLMClient

warnings.warn(
    "kairos.llm.mcp_client is deprecated; import from kairos.llm.providers instead. "
    "The llm-mcp backend was removed in kairos 0.4 and this shim will be removed in 0.5.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["LLMClient", "LLMError", "LLMResult", "MCPUnreachable", "StubLLMClient"]
