"""kairos - A CLI for executable agent knowledge.

Implements Karpathy's LLM Wiki pattern (raw/ -> wiki/ -> AGENTS.md schema)
with three operations (ingest, query, lint), a technique selector, and
runners for RAG, ReAct, and Reflexion. Model calls route through the configured
direct backend: stub, Ollama, OpenAI, Anthropic, or OpenAI-compatible.
"""

__version__ = "0.4.0"
