"""Emit a CI artifact showing the KAI2 closure matrix."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _closure_matrix() -> dict[str, tuple[str, str]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests.regression.v2.matrix import CLOSURE_MATRIX

    return CLOSURE_MATRIX


def main() -> int:
    closure_matrix = _closure_matrix()
    print("v2_verification.py - KAI2-001..030 closure guards")
    print(f"repo: {ROOT}")
    print()
    print(f"{'ID':<12}{'STATUS':<10}GUARD")
    print("-" * 80)
    for kid in sorted(closure_matrix):
        relative_path, marker = closure_matrix[kid]
        path = ROOT / relative_path
        status = "Fixed" if path.exists() and marker in path.read_text(encoding="utf-8") else "Missing"
        print(f"{kid:<12}{status:<10}{relative_path} :: {marker}")
        if status != "Fixed":
            return 1
    print()
    print("Summary: 0 Open, 30 Fixed, 0 Missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
