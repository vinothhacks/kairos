"""kairos - A CLI for executable agent knowledge.

Implements Karpathy's LLM Wiki pattern (raw/ -> wiki/ -> AGENTS.md schema)
with three operations (ingest, query, lint), a technique selector, and
runners for RAG, ReAct, and Reflexion. All model calls are routed through
llm-mcp; no API keys required.
"""

__version__ = "0.3.0"
