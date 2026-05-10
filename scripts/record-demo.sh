#!/usr/bin/env sh
# Record the kairos demo asciicast and convert to GIF.
#
# Requires: asciinema (https://docs.asciinema.org/), agg (https://github.com/asciinema/agg).
#   brew install asciinema agg               # macOS
#   pip install asciinema && cargo install --git https://github.com/asciinema/agg.git
#
# Output: assets/demo.cast and assets/demo.gif
set -eu

DIR=$(cd "$(dirname "$0")" && pwd)
ROOT="$DIR/.."
ASSETS="$ROOT/assets"
OUT_CAST="$ASSETS/demo.cast"
OUT_GIF="$ASSETS/demo.gif"

if ! command -v asciinema >/dev/null 2>&1; then
  echo "FAIL: asciinema not installed (https://docs.asciinema.org/)"
  exit 1
fi
if ! command -v agg >/dev/null 2>&1; then
  echo "FAIL: agg not installed (https://github.com/asciinema/agg)"
  exit 1
fi

mkdir -p "$ASSETS"
rm -f /tmp/kairos-demo
mkdir -p /tmp/kairos-demo

cat >"$DIR/_demo-script.sh" <<'EOS'
#!/usr/bin/env sh
set -eu
cd /tmp/kairos-demo

clear
echo '$ kairos init my-wiki'
sleep 1
KAIROS_LLM_BACKEND=stub kairos init my-wiki
sleep 2

cd my-wiki
clear
echo '$ kairos run "Search the docs and summarize caching" --dry'
sleep 1
KAIROS_LLM_BACKEND=stub kairos run "Search the docs and summarize caching" --dry
sleep 3

clear
echo '$ kairos lint'
sleep 1
KAIROS_LLM_BACKEND=stub kairos lint
sleep 3

clear
echo '# 21 seed pages, 3 runners, zero API keys.'
echo '# pip install kairos-agent'
sleep 4
EOS
chmod +x "$DIR/_demo-script.sh"

echo "==> recording asciicast -> $OUT_CAST"
asciinema rec -c "$DIR/_demo-script.sh" --idle-time-limit 1.5 --overwrite "$OUT_CAST"

echo "==> rendering GIF -> $OUT_GIF"
agg --theme monokai --speed 1.4 --font-size 16 "$OUT_CAST" "$OUT_GIF"

rm -f "$DIR/_demo-script.sh"

echo
echo "DONE: $OUT_GIF"
