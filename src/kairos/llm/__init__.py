"""LLM bridge - talks to a running llm-mcp server.

All ChatGPT and Claude calls fan through this module so the rest of kairos
never imports any provider SDK directly.
"""
from kairos.llm.mcp_client import LLMClient, LLMError, MCPUnreachable

__all__ = ["LLMClient", "LLMError", "MCPUnreachable"]
