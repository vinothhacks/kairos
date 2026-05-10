"""Memory layer: SQLite-backed run logs, feedback, derived wiki indices."""
from kairos.memory.db import Database, ensure_schema

__all__ = ["Database", "ensure_schema"]
