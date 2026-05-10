#!/usr/bin/env sh
# e2e 01: kairos init bootstraps a project with the seed wiki.
# Run from the kairos repo root: ./scripts/e2e/01_init.sh
set -eu

ROOT="${KAIROS_E2E_ROOT:-/tmp/kairos-e2e}"
rm -rf "$ROOT"
mkdir -p "$ROOT"

echo "==> kairos init $ROOT"
KAIROS_LLM_BACKEND=stub uv run kairos init "$ROOT"

echo
echo "==> verify AGENTS.md exists"
test -f "$ROOT/AGENTS.md" || { echo "FAIL: AGENTS.md missing"; exit 1; }

echo "==> verify wiki/index.md exists"
test -f "$ROOT/wiki/index.md" || { echo "FAIL: wiki/index.md missing"; exit 1; }

echo "==> verify seed concepts copied"
SEED_COUNT=$(find "$ROOT/wiki/concepts" -name "*.md" | wc -l)
echo "    seeded concept pages: $SEED_COUNT"
test "$SEED_COUNT" -ge 20 || { echo "FAIL: expected >=20 concept pages, got $SEED_COUNT"; exit 1; }

echo "==> verify required pages present"
for SLUG in rag react reflexion chain-of-thought tree-of-thoughts llm-wiki; do
  test -f "$ROOT/wiki/concepts/$SLUG.md" || { echo "FAIL: $SLUG.md missing"; exit 1; }
done

echo
echo "PASS: init"
