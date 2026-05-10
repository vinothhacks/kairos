#!/usr/bin/env sh
# e2e 02: kairos ingest reads a raw source and proposes wiki updates.
# Uses the stub LLM client so this runs offline.
set -eu

ROOT="${KAIROS_E2E_ROOT:-/tmp/kairos-e2e}"
test -d "$ROOT" || { echo "run 01_init.sh first"; exit 1; }

mkdir -p "$ROOT/raw/articles"
cat >"$ROOT/raw/articles/sample.md" <<'EOF'
# Sample article on agent caching

Caching agent intermediate results dramatically reduces cost. The simplest pattern is content-addressed caching of LLM responses keyed on prompt hash. More advanced systems cache at the tool-call level so that re-running a ReAct trace replays cached observations.
EOF

echo "==> kairos ingest $ROOT/raw/articles/sample.md"
KAIROS_LLM_BACKEND=stub uv run kairos ingest "$ROOT/raw/articles/sample.md" --project "$ROOT" || {
  echo "FAIL: ingest exited non-zero"
  exit 1
}

echo "==> verify a source page was written"
SRC_COUNT=$(find "$ROOT/wiki/sources" -name "*.md" 2>/dev/null | wc -l || echo 0)
test "$SRC_COUNT" -ge 1 || { echo "FAIL: expected >=1 source page, got $SRC_COUNT"; exit 1; }

echo "==> verify log was appended"
grep -q "ingest" "$ROOT/wiki/log.md" || { echo "FAIL: log.md has no ingest entry"; exit 1; }

echo
echo "PASS: ingest"
