#!/usr/bin/env sh
# e2e 05: kairos run picks a technique and dispatches a runner.
# Verifies all 3 techniques (rag/react/reflexion) plus auto-selection.
set -eu

ROOT="${KAIROS_E2E_ROOT:-/tmp/kairos-e2e}"
test -d "$ROOT" || { echo "run 01_init.sh first"; exit 1; }

echo "==> 1. auto + --dry: top-3 ranking"
KAIROS_LLM_BACKEND=stub uv run kairos run "Search the docs and summarize the caching section" --project "$ROOT" --dry

echo
echo "==> 2. force technique=rag"
KAIROS_LLM_BACKEND=stub uv run kairos run "Synthesize an answer from retrieved chunks" --project "$ROOT" --technique rag

echo
echo "==> 3. force technique=react"
KAIROS_LLM_BACKEND=stub uv run kairos run "Use tools to find the answer" --project "$ROOT" --technique react

echo
echo "==> 4. force technique=reflexion"
KAIROS_LLM_BACKEND=stub uv run kairos run "Draft and refine a paragraph about RAG" --project "$ROOT" --technique reflexion

echo
echo "==> 5. verify run rows in kairos.db"
DB="$ROOT/.kairos/kairos.db"
test -f "$DB" || { echo "FAIL: $DB not found"; exit 1; }

if command -v sqlite3 >/dev/null 2>&1; then
  COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM runs;")
  echo "    runs in db: $COUNT"
  test "$COUNT" -ge 3 || { echo "FAIL: expected >=3 runs, got $COUNT"; exit 1; }
else
  echo "    (sqlite3 CLI not installed, skipping row-count check)"
fi

echo
echo "PASS: run"
