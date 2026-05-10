#!/usr/bin/env sh
# e2e 04: kairos lint runs local checks + LLM contradiction pass and writes a report.
set -eu

ROOT="${KAIROS_E2E_ROOT:-/tmp/kairos-e2e}"
test -d "$ROOT" || { echo "run 01_init.sh first"; exit 1; }

echo "==> kairos lint -p $ROOT"
KAIROS_LLM_BACKEND=stub uv run kairos lint -p "$ROOT"

echo
echo "==> verify lint report was written"
REPORT=$(find "$ROOT/outputs" -name "lint-*.md" 2>/dev/null | head -n 1)
test -n "$REPORT" || { echo "FAIL: no lint report in $ROOT/outputs/"; exit 1; }
echo "    report: $REPORT"

echo
echo "==> verify report has scan count and finding header"
grep -q "Pages scanned:" "$REPORT" || { echo "FAIL: report missing 'Pages scanned:'"; exit 1; }
grep -q "Findings:" "$REPORT" || { echo "FAIL: report missing 'Findings:'"; exit 1; }

echo
echo "PASS: lint"
