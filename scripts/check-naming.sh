#!/usr/bin/env bash
# Gate 4 of the "remove derivativeness from upstream" epic (Mesh #f3eb7b30):
# how many NAMES our src/ still shares with upstream — files, directories,
# types, class members, exports.
#
# Gates 1-3 read the contents of lines. None of them reads what a thing is
# CALLED, so a file can pass all three and still hand a reader upstream's map
# on sight. This closes that axis.
#
#   ./scripts/check-naming.sh                     # measure, exit 0
#   ./scripts/check-naming.sh --max-work 0        # gate: exit 1 if work > 0
#   ./scripts/check-naming.sh --self-test         # controls; run before trusting it
#   ./scripts/check-naming.sh --json out.json --show-samples all.tsv
#
# Exit 0 = under the cap (or reporting only), 1 = work remains, 2 = the probe
# could not run. It never reports clean when it failed to look.
set -euo pipefail

# Same pin as gates 1-3 — the commit our initial import (b2e3e60, 2026-02-05)
# was copied from. A derivative-work question is about the code we took, not
# about whatever upstream looks like today. Measured 2026-08-23: upstream HEAD
# has 246 src files against the fork point's 155, so scoring against HEAD would
# flatter us with names UPSTREAM has since moved. Do not swap this for HEAD.
FORK_POINT="d1b24af2"
UPSTREAM_REPO="${UPSTREAM_REPO_URL:?UPSTREAM_REPO_URL is not set - refusing to run a baseline gate with no baseline}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
GATE="$REPO_ROOT/scripts/check-naming.py"
UPSTREAM_REF="$FORK_POINT"
SELFTEST=0
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream) UPSTREAM_REF="$2"; shift 2 ;;
    --self-test) SELFTEST=1; shift ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== cloning upstream $UPSTREAM_REPO ..."
git clone --quiet "$UPSTREAM_REPO" "$WORK/upstream" \
  || { echo "FATAL: upstream clone failed"; exit 2; }
if [[ "$UPSTREAM_REF" == "HEAD" ]]; then
  UPSTREAM_SHA="$(git -C "$WORK/upstream" rev-parse --short HEAD)"
else
  UPSTREAM_SHA="$UPSTREAM_REF"
fi
git -C "$WORK/upstream" checkout --quiet "$UPSTREAM_SHA" \
  || { echo "FATAL: upstream commit $UPSTREAM_SHA not found"; exit 2; }
echo "== upstream pinned at $UPSTREAM_SHA ($(git -C "$WORK/upstream" log -1 --format=%ad --date=short))"
echo "== ours at $(git -C "$REPO_ROOT" rev-parse --short HEAD)"
echo

if [[ "$SELFTEST" == "1" ]]; then
  # A gate that cannot go red is worse than no gate: it reads as a clean bill
  # of health forever. Both directions are checked, because "always green" and
  # "always red" are both failures and only one of them is noticeable.
  fail=0

  echo "-- POSITIVE control: upstream measured against a copy of ITSELF."
  echo "   Every name is shared by construction, so the gate MUST go red."
  cp -R "$WORK/upstream/src" "$WORK/identical"
  set +e
  out="$("$PY" "$GATE" "$WORK/upstream/src" "$WORK/identical" --max-work 0 --limit 0 2>&1)"
  rc=$?
  set -e
  echo "$out" | sed -n '/^axis/,/^TOTAL/p' | sed 's/^/   /'
  if [[ $rc -eq 1 ]]; then
    echo "   PASS: exit 1 on identical input"
  else
    echo "   FAIL: exit $rc on identical input — the gate cannot go red"; fail=1
  fi

  echo
  echo "-- NEGATIVE control: upstream measured against a tree that shares"
  echo "   nothing. The gate MUST come back green with an empty work basket."
  mkdir -p "$WORK/disjoint/qqzz"
  cat > "$WORK/disjoint/qqzz/Zzqq.ts" <<'TSEOF'
export class ZzqqWidgetHolder {
	private zzqqSlotCount = 0;
	zzqqAdvanceSlot(): number {
		return ++this.zzqqSlotCount;
	}
}
export const zzqqDefaultHolder = new ZzqqWidgetHolder();
TSEOF
  set +e
  out="$("$PY" "$GATE" "$WORK/upstream/src" "$WORK/disjoint" --max-work 0 --limit 0 2>&1)"
  rc=$?
  set -e
  echo "$out" | sed -n '/^axis/,/^TOTAL/p' | sed 's/^/   /'
  if [[ $rc -eq 0 ]] && echo "$out" | grep -q '^TOTAL *0 *0 *0 *0 *0$'; then
    echo "   PASS: exit 0, work basket empty on a disjoint tree"
  else
    echo "   FAIL: exit $rc / non-empty basket on a disjoint tree"; fail=1
  fi

  echo
  if [[ $fail -eq 0 ]]; then echo "SELF-TEST PASS"; exit 0; fi
  echo "SELF-TEST FAIL — do not trust this gate's number until fixed"; exit 2
fi

"$PY" "$GATE" "$WORK/upstream/src" "$REPO_ROOT/src" ${EXTRA[@]+"${EXTRA[@]}"}
