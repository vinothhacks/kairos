"""KAI2 closure matrix.

The issue-2 audit shipped as prose + repro scripts. This matrix keeps every
KAI2-001..030 finding tied to an executable regression file or a static CI gate
so future releases cannot accidentally drop coverage for part of the audit.
"""
from __future__ import annotations

from pathlib import Path

from tests.regression.v2.matrix import CLOSURE_MATRIX

ROOT = Path(__file__).resolve().parents[3]


def test_every_kai2_finding_has_a_regression_guard() -> None:
    expected = {f"KAI2-{i:03d}" for i in range(1, 31)}

    assert set(CLOSURE_MATRIX) == expected
    for kid, (relative_path, marker) in CLOSURE_MATRIX.items():
        path = ROOT / relative_path
        assert path.exists(), f"{kid}: missing guard file {relative_path}"
        assert marker in path.read_text(encoding="utf-8"), f"{kid}: missing marker {marker!r}"
