#!/usr/bin/env sh
# Run all 5 kairos e2e scripts in order. Use as a smoke-test before release.
set -eu

DIR=$(cd "$(dirname "$0")" && pwd)

echo "============================================================"
echo " kairos e2e suite"
echo "============================================================"

for SCRIPT in 01_init.sh 02_ingest.sh 03_query.sh 04_lint.sh 05_run.sh; do
  echo
  echo "############################################################"
  echo "# $SCRIPT"
  echo "############################################################"
  sh "$DIR/$SCRIPT"
done

echo
echo "============================================================"
echo " ALL E2E PASSED"
echo "============================================================"
