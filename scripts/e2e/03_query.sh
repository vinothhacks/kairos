#!/usr/bin/env sh
# e2e 03: kairos query lexically retrieves and synthesizes (stub answer).
set -eu

ROOT="${KAIROS_E2E_ROOT:-/tmp/kairos-e2e}"
test -d "$ROOT" || { echo "run 01_init.sh first"; exit 1; }

echo "==> kairos query 'When to use ReAct over RAG?'"
OUT=$(KAIROS_LLM_BACKEND=stub uv run kairos query "When to use ReAct over RAG?" --project "$ROOT")
echo "$OUT"

echo
echo "==> verify >=1 page was read"
echo "$OUT" | grep -E "read [0-9]+ page" >/dev/null || {
  echo "FAIL: query did not report pages read"
  exit 1
}

echo
echo "PASS: query"
