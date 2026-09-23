#!/usr/bin/env bash
# Gate 4 of the whole-file similarity legal gates (#f3eb7b30): how many
# NAMES our src/ still shares with the baseline tree — files, directories,
# types, class members, exports.
#
# Gates 1-3 read the contents of lines. None of them reads what a thing is
# CALLED, so a file can pass all three and still hand a reader a one-to-one
# map onto the baseline on sight. This closes that axis.
#
#   ./scripts/check-naming.sh                     # measure, exit 0
#   ./scripts/check-naming.sh --max-work 0        # gate: exit 1 if work > 0
#   ./scripts/check-naming.sh --self-test         # controls; run before trusting it
#   ./scripts/check-naming.sh --json out.json --show-samples all.tsv
#
# Exit 0 = under the cap (or reporting only), 1 = work remains, 2 = the probe
# could not run. It never reports clean when it failed to look.
set -euo pipefail

# Same pin as gates 1-3. A similarity question is about the code we took at
# import time, not about whatever the baseline tree looks like today.
# Measured 2026-08-23: the baseline's current HEAD has substantially more
# src files than the pinned commit, so scoring against HEAD would flatter us
# with names the baseline has since moved. Do not swap this for HEAD.
PINNED_COMMIT="${PINNED_COMMIT:?PINNED_COMMIT is not set - refusing to run a baseline gate with no baseline}"
BASELINE_REPO="${BASELINE_REPO_URL:?BASELINE_REPO_URL is not set - refusing to run a baseline gate with no baseline}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
GATE="$REPO_ROOT/scripts/check-naming.py"
BASELINE_REF="$PINNED_COMMIT"
SELFTEST=0
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --baseline) BASELINE_REF="$2"; shift 2 ;;
    --self-test) SELFTEST=1; shift ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== cloning baseline $BASELINE_REPO ..."
git clone --quiet "$BASELINE_REPO" "$WORK/baseline" \
  || { echo "FATAL: baseline clone failed"; exit 2; }
if [[ "$BASELINE_REF" == "HEAD" ]]; then
  BASELINE_SHA="$(git -C "$WORK/baseline" rev-parse --short HEAD)"
else
  BASELINE_SHA="$BASELINE_REF"
fi
git -C "$WORK/baseline" checkout --quiet "$BASELINE_SHA" \
  || { echo "FATAL: baseline commit $BASELINE_SHA not found"; exit 2; }
echo "== baseline pinned at $BASELINE_SHA ($(git -C "$WORK/baseline" log -1 --format=%ad --date=short))"
echo "== ours at $(git -C "$REPO_ROOT" rev-parse --short HEAD)"
echo

if [[ "$SELFTEST" == "1" ]]; then
  # A gate that cannot go red is worse than no gate: it reads as a clean bill
  # of health forever. Both directions are checked, because "always green" and
  # "always red" are both failures and only one of them is noticeable.
  fail=0

  echo "-- POSITIVE control: baseline measured against a copy of ITSELF."
  echo "   Every name is shared by construction, so the gate MUST go red."
  cp -R "$WORK/baseline/src" "$WORK/identical"
  set +e
  out="$("$PY" "$GATE" "$WORK/baseline/src" "$WORK/identical" --max-work 0 --limit 0 2>&1)"
  rc=$?
  set -e
  echo "$out" | sed -n '/^axis/,/^TOTAL/p' | sed 's/^/   /'
  if [[ $rc -eq 1 ]]; then
    echo "   PASS: exit 1 on identical input"
  else
    echo "   FAIL: exit $rc on identical input — the gate cannot go red"; fail=1
  fi

  echo
  echo "-- NEGATIVE control: baseline measured against a tree that shares"
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
  out="$("$PY" "$GATE" "$WORK/baseline/src" "$WORK/disjoint" --max-work 0 --limit 0 2>&1)"
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

"$PY" "$GATE" "$WORK/baseline/src" "$REPO_ROOT/src" ${EXTRA[@]+"${EXTRA[@]}"}
