#!/usr/bin/env bash
# Acceptance probe for the "remove derivativeness from upstream" epic (Mesh #f3eb7b30).
#
# Clones the upstream project at a PINNED commit and reports how many of our src/ files
# are still >= 70% similar to it. Exit 0 = acceptance met, 1 = work remains, 2 = probe
# could not run (never reports "clean" when it failed to look).
#
#   ./scripts/check-derivativeness.sh                 # vs the pinned fork-point (default)
#   ./scripts/check-derivativeness.sh --upstream HEAD # vs upstream's current main
#   ./scripts/check-derivativeness.sh --json out.json
set -euo pipefail

# The commit our initial import (b2e3e60, 2026-02-05) was copied from. This is the baseline
# that matters: a derivative-work question is about the code we actually took, not about
# whatever upstream happens to look like today. Measured 2026-08-20: scoring against
# upstream HEAD instead flattered us by 36 files that only "cleared" because UPSTREAM
# rewrote them. Do not swap this for HEAD to make the number look better.
FORK_POINT="d1b24af2"
UPSTREAM_REPO="${UPSTREAM_REPO_URL:?UPSTREAM_REPO_URL is not set - refusing to run a baseline gate with no baseline}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_REF="$FORK_POINT"
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream) UPSTREAM_REF="$2"; shift 2 ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== cloning upstream $UPSTREAM_REPO ..."
git clone --quiet "$UPSTREAM_REPO" "$WORK/upstream" || { echo "FATAL: upstream clone failed"; exit 2; }
if [[ "$UPSTREAM_REF" == "HEAD" ]]; then
  UPSTREAM_SHA="$(git -C "$WORK/upstream" rev-parse --short HEAD)"
else
  UPSTREAM_SHA="$UPSTREAM_REF"
fi
git -C "$WORK/upstream" checkout --quiet "$UPSTREAM_SHA" || { echo "FATAL: upstream commit $UPSTREAM_SHA not found"; exit 2; }
echo "== upstream pinned at $UPSTREAM_SHA ($(git -C "$WORK/upstream" log -1 --format=%ad --date=short))"
echo "== ours at $(git -C "$REPO_ROOT" rev-parse --short HEAD)"
echo

PY="${PYTHON:-python3}"
"$PY" "$REPO_ROOT/scripts/measure-derivativeness.py" \
  "$REPO_ROOT/src" "$WORK/upstream/src" ${EXTRA[@]+"${EXTRA[@]}"}
