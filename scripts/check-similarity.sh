#!/usr/bin/env bash
# Acceptance probe for the whole-file similarity legal gate (#f3eb7b30).
#
# Clones the baseline tree at a PINNED commit and reports how many of our src/ files
# are still >= 70% similar to it. Exit 0 = acceptance met, 1 = work remains, 2 = probe
# could not run (never reports "clean" when it failed to look).
#
#   ./scripts/check-similarity.sh                  # vs the pinned baseline commit (default)
#   ./scripts/check-similarity.sh --baseline HEAD  # vs the baseline's current main
#   ./scripts/check-similarity.sh --json out.json
set -euo pipefail

# This is the baseline that matters: a similarity question is about the code we
# actually took at import time, not about whatever the baseline tree happens to
# look like today. Measured 2026-08-20: scoring against the baseline's current HEAD
# instead flattered us by dozens of files that only "cleared" because the baseline
# itself had since rewritten them. Do not swap this for HEAD to make the number
# look better.
PINNED_COMMIT="${PINNED_COMMIT:?PINNED_COMMIT is not set - refusing to run a baseline gate with no baseline}"
BASELINE_REPO="${BASELINE_REPO_URL:?BASELINE_REPO_URL is not set - refusing to run a baseline gate with no baseline}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASELINE_REF="$PINNED_COMMIT"
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --baseline) BASELINE_REF="$2"; shift 2 ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== cloning baseline $BASELINE_REPO ..."
git clone --quiet "$BASELINE_REPO" "$WORK/baseline" || { echo "FATAL: baseline clone failed"; exit 2; }
if [[ "$BASELINE_REF" == "HEAD" ]]; then
  BASELINE_SHA="$(git -C "$WORK/baseline" rev-parse --short HEAD)"
else
  BASELINE_SHA="$BASELINE_REF"
fi
git -C "$WORK/baseline" checkout --quiet "$BASELINE_SHA" || { echo "FATAL: baseline commit $BASELINE_SHA not found"; exit 2; }
echo "== baseline pinned at $BASELINE_SHA ($(git -C "$WORK/baseline" log -1 --format=%ad --date=short))"
echo "== ours at $(git -C "$REPO_ROOT" rev-parse --short HEAD)"
echo

PY="${PYTHON:-python3}"
"$PY" "$REPO_ROOT/scripts/measure-similarity.py" \
  "$REPO_ROOT/src" "$WORK/baseline/src" ${EXTRA[@]+"${EXTRA[@]}"}
