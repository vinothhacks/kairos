#!/usr/bin/env sh
# kairos installer (POSIX). Idempotent. Picks `uv tool install` if available,
# otherwise `pipx install`, otherwise `pip install --user`.
set -eu

VERSION="${KAIROS_VERSION:-0.3.0}"
PKG="kairos-agent==$VERSION"
BIN="kairos"
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

say() { printf "%b\n" "$1"; }
ok()  { say "${GREEN}\xe2\x9c\x94${NC} $1"; }
hi()  { say "${CYAN}\xe2\x86\x92${NC} $1"; }
err() { say "${RED}!${NC} $1" >&2; exit 1; }

hi "kairos installer \xe2\x80\x94 picks the right Python tool for you"

# Prefer uv (fastest, isolated tools dir).
if command -v uv >/dev/null 2>&1; then
  hi "found uv, installing as a uv tool"
  uv tool install "$PKG" || err "uv tool install failed"
  ok "installed via uv"
elif command -v pipx >/dev/null 2>&1; then
  hi "found pipx, installing as an isolated app"
  pipx install "$PKG" || err "pipx install failed"
  ok "installed via pipx"
elif command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1; then
  PIP="${PIP:-$(command -v pip3 || command -v pip)}"
  hi "no uv or pipx, falling back to $PIP --user"
  "$PIP" install --user --upgrade "$PKG" || err "pip install failed"
  ok "installed via pip --user"
else
  err "no Python package manager found. Install uv (https://docs.astral.sh/uv/) or pipx and re-run."
fi

if command -v "$BIN" >/dev/null 2>&1; then
  VERS="$("$BIN" version 2>/dev/null || echo "?")"
  ok "$BIN on PATH: $VERS"
  say ""
  say "${DIM}next:${NC}"
  say "  $BIN init my-wiki && cd my-wiki"
  say "  $BIN run 'Search the docs for caching' --dry"
else
  say ""
  say "${DIM}note:${NC} kairos installed but not on PATH. With uv:"
  say "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
