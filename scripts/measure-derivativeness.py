#!/usr/bin/env python3
"""Acceptance probe for epic #f3eb7b30 — how derivative is our plugin's src/ vs upstream No-Instructions/Relay.

Usage: measure-derivativeness.py <ours_src_dir> <upstream_src_dir> [--json out.json] [--threshold 0.70]

Two independent similarity ratios per name-matched file:
  char  = difflib.SequenceMatcher over raw characters (autojunk on — the fast default)
  line  = difflib.SequenceMatcher over lines (autojunk off)
A file counts AGAINST acceptance when max(char, line) >= threshold. Using the max is
deliberate and conservative: a file only clears once it is under the bar by BOTH measures,
so the number cannot be improved by picking whichever metric happens to be friendlier.

Exit 0 == acceptance met (zero files at/above threshold), exit 1 == work remains,
exit 2 == the probe could not run (missing/empty input) — never silently "clean".
"""
import sys, os, json, difflib

# Directories vendored from a THIRD party (not from upstream). Both we and upstream copied
# these from their real authors, so they are near-identical BY CONSTRUCTION and rewriting them
# would be pointless — and for the LICENSE files actively wrong. They are excluded from the
# acceptance count and reported separately. Provenance is stated inside the files themselves:
#   y-codemirror.next/  -> Kevin Jahns (yjs), MIT, "adapted from y-codemirror.next"
#   client/provider.ts  -> "Adapted from y-websocket" (yjs)
#   storage/y-indexeddb.js -> y-indexeddb (yjs)
#   pocketbase/         -> Gani Georgiev, pocketbase/js-sdk, MIT
# "pocketbase/" dropped 2026-08-23 (Mesh #84bd2a91) -- the directory no longer
# exists in src/, so the prefix could only ever excuse a future file put there.
VENDORED_THIRD_PARTY = ("y-codemirror.next/", "client/", "storage/")

def is_vendored(relpath):
    return relpath.replace(os.sep, "/").startswith(VENDORED_THIRD_PARTY)

def rel_files(root):
    out = {}
    for dirpath, _, names in os.walk(root):
        for n in names:
            full = os.path.join(dirpath, n)
            out[os.path.relpath(full, root)] = full
    return out

def main():
    if len(sys.argv) < 3:
        print("usage: measure-derivativeness.py <ours_src> <upstream_src> [--json out] [--threshold 0.70]")
        return 2
    ours_root, up_root = sys.argv[1], sys.argv[2]
    thr = float(sys.argv[sys.argv.index('--threshold') + 1]) if '--threshold' in sys.argv else 0.70
    ours, up = rel_files(ours_root), rel_files(up_root)
    if not ours or not up:
        print(f"FATAL: empty input tree (ours={len(ours)} upstream={len(up)}) — probe cannot run")
        return 2
    common = sorted(set(ours) & set(up))
    if not common:
        print("FATAL: zero name-matched files — wrong directories? refusing to report 'clean'")
        return 2
    rows = []
    for rp in common:
        a = open(ours[rp], 'rb').read()
        b = open(up[rp], 'rb').read()
        identical = (a == b)
        try:
            ta, tb = a.decode('utf-8'), b.decode('utf-8')
        except UnicodeDecodeError:
            char = line = (1.0 if identical else 0.0)
        else:
            char = difflib.SequenceMatcher(None, ta, tb).ratio()
            line = difflib.SequenceMatcher(None, ta.splitlines(True), tb.splitlines(True), autojunk=False).ratio()
        rows.append({'file': rp, 'char': round(char, 4), 'line': round(line, 4),
                     'score': round(max(char, line), 4), 'identical': identical,
                     'our_bytes': len(a), 'up_bytes': len(b)})
    for r in rows:
        r['vendored'] = is_vendored(r['file'])
    rows.sort(key=lambda r: (-r['score'], -r['our_bytes']))
    over = [r for r in rows if r['score'] >= thr and not r['vendored']]
    vendored_over = [r for r in rows if r['score'] >= thr and r['vendored']]
    summary = {'threshold': thr, 'ours_total_files': len(ours), 'upstream_total_files': len(up),
               'name_matched': len(common), 'identical': sum(r['identical'] for r in rows),
               'ge90': sum(1 for r in rows if r['score'] >= 0.90),
               'over_threshold': len(over),
               'over_threshold_our_bytes': sum(r['our_bytes'] for r in over),
               'vendored_over_threshold': len(vendored_over)}
    print("=== SUMMARY ===")
    for k, v in summary.items():
        print(f"{k:26s} {v}")
    print(f"\n=== {len(over)} FILES >= {thr} (the work-list), by score then size ===")
    for r in over:
        print(f"{r['score']:.4f} (c={r['char']:.4f} l={r['line']:.4f}) {'IDENT' if r['identical'] else '     '} {r['our_bytes']:7d}B  {r['file']}")
    if vendored_over:
        print(f"\n=== {len(vendored_over)} vendored third-party files also >= {thr} — EXCLUDED from acceptance ===")
        print("    (identical because both projects copied the same third-party library;")
        print("     the fix is correct attribution or using the npm package, never a rewrite)")
        for r in vendored_over:
            print(f"    {r['score']:.4f} {r['our_bytes']:7d}B  {r['file']}")
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        json.dump({'summary': summary, 'rows': rows}, open(out, 'w'), indent=2)
        print(f"\nwrote {out}")
    return 0 if not over else 1

if __name__ == '__main__':
    sys.exit(main())
