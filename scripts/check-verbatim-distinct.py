#!/usr/bin/env python3
"""Gate 3: DISTINGUISHABLE verbatim lines retained from upstream, per file.

Why not raw retention. `check-verbatim-overlap.py` counts every substantive line
that survives, order-free. On a Svelte component that over-counts badly: measured
2026-08-21, `components/HelpPopover.svelte` shows run=0 and 79% raw retention, and
the retained lines are `<script lang="ts">`, `let isVisible = false;`,
`export let helpText: string;`, `bind:this={buttonEl}` — framework scaffolding that
two independent implementations of the same component MUST share. Building a gate on
raw % would demand rewriting things that cannot be written differently.

The question the gate exists to approximate is "would the upstream author recognise
his own code here". That is answered by lines carrying AUTHORED content: his log and
error wording, his identifiers in non-trivial statements. This counts those.

A retained line is DISTINGUISHABLE when it is not framework boilerplate AND either
carries a quoted literal of >=10 chars, or is a substantial statement (>=40 chars).
The classifier is a heuristic and is meant to be audited: `--show-samples` prints
what it called distinguishable and what it discarded, so the definition can be
argued with rather than trusted.

Usage:
  check-verbatim-distinct.py <upstream_src> <our_src> [--max-distinct N]
                             [--show-samples FILE] [--json out.json]
Exit 1 if any in-scope file exceeds --max-distinct (default: report only).
"""
import json
import os
import re
import sys
from collections import Counter

# This is currently the ONLY place these three baskets are enumerated for the
# epic's derivativeness gates: check-verbatim-runs.py (gate 2) walks every
# upstream file with no basket concept at all, and measure-derivativeness.py
# (gate 1) only knows a broader whole-directory VENDORED_THIRD_PARTY prefix
# list, not do-not-touch/adjudicated. If a future gate grows its own basket
# lists, import these rather than re-typing them — two hand-copies of the
# same list drift apart silently (Mesh #6b88fc6f point 5).
# Named per file, not by directory prefix — a prefix silently annexes any file
# later added under that path without a fresh "is this really vendor" check.
# The entries here are honest third-party code with their own upstream LICENSE
# headers (y-codemirror.next: Kevin Jahns; client/provider.ts and
# storage/y-indexeddb.js: adapted from Kevin Jahns' y-websocket / y-indexeddb),
# confirmed by independent verifier review (Mesh #8bac4985).
#
# This basket SHRINKS as vendoring is cleared (Mesh #84bd2a91). An entry may be
# removed only when the file is gone from src/ -- never because it stopped
# looking derivative. Two were removed on 2026-08-23:
#   pocketbase/LocalAuthStore.ts -> replaced by our auth/VaultCredentialStore.ts,
#       written against BaseAuthStore, a public API of the pocketbase dependency
#       we already ship. No Gani Georgiev code remains.
#   client/types.ts -> replaced by our relay/TokenShapes.ts. What was copied
#       from y-sweet (the base64 helpers) was dead code, called from nowhere in
#       the repo; the interfaces had already diverged into our own wire format.
VENDOR_FILES = frozenset({
    'y-codemirror.next/LiveEditPlugin.ts',
    'y-codemirror.next/LiveNodePlugin.ts',
    'y-codemirror.next/PositionTransformer.ts',
    'y-codemirror.next/RemoteSelections.ts',
    'y-codemirror.next/YRange.ts',
    'storage/y-indexeddb.js',
    'client/provider.ts',
})
DO_NOT_TOUCH = set()
# Wave 4 adjudication (Mesh #0ec60ab6, decided in the 23.08 10:19 comment;
# executed via #7685292e): all 20 files still over threshold after waves
# A1/A2/B1/B2 carry zero remaining author comments -- what's left is
# Obsidian/DOM contracts and our own API calls/idioms, not prose that could
# be reworded without becoming the variable/structure shuffling gate 3
# exists to catch. Confirmed by hand on differ/differencesView.ts before
# this call: the retained lines are `cls: "file-diff__line"`,
# `lineDiv.classList.add(...)`, `export class DifferencesView extends
# ItemView {`, `await this.app.vault.modify(...)`.
#
# Pruned to the live set gate4 W7d (#b2cf036c): 22 of the original 24
# ADJUDICATED entries, and all 3 original DO_NOT_TOUCH entries, named files
# renamed or removed by earlier gate4 waves and no longer present on disk --
# a basket that is 92% dead names is misread by the next person to open it.
# Only Document.ts and main.ts (both here for their own reasons -- see
# CONVERGENT_FILES / PLATFORM_CONVENTION_FILES in check-naming.py) still
# exist. This is cleanup, not a loosening: a removed entry referenced
# nothing, so the gate's live behavior on the current tree is unchanged
# (verified exit 0 before and after, same as the file it never matched).
ADJUDICATED = {
    'Document.ts', 'main.ts',
}

BOILERPLATE = (
    re.compile(r'^import\b'),
    # Only a BARE declaration, or one initialized to a value from the SAME
    # trivial set the let/const/var rule below already treats as content-
    # free, is framework shape. `export let helpText: string;` and `export
    # let x: T | undefined = undefined;` say nothing an author chose; `export
    # let errorLog = curryLog("...", "error");` has a real value, which is
    # data, not scaffolding — and used to slip past distinguishable() below
    # because this regex's `.*` swallowed everything up to the trailing `;`,
    # trivial or not.
    re.compile(
        r'^export\s+(let|const|type|interface|default)\b'
        r'(?:(?!.*=).*[:;]\s*$'
        r'|.*=\s*(false|true|null|undefined|0|\[\]|\{\}|""|\'\')\s*;\s*$)'
    ),
    re.compile(r'^</?(script|style|div|span|button|slot)\b'),
    re.compile(r'^(let|const|var)\s+\w+(\s*:\s*[\w<>\[\]|.\s]+)?'
               r'(\s*=\s*(false|true|null|undefined|0|\[\]|\{\}|""|\'\'))?\s*;?$'),
    re.compile(r'^[a-z-]+\s*:\s*[^;{]+;$'),            # a CSS declaration
    re.compile(r'^(bind|on|class|type|aria-[\w-]+|style|role)[:=]'),
    re.compile(r'^\}?\s*(else|catch|finally|try)\s*\{?$'),
    re.compile(r'^@(media|keyframes|import)\b'),
    re.compile(r'^(public|private|protected)?\s*\w+\s*\([^)]*\)\s*\{?$'),
)
LITERAL = re.compile(r'''(["'`])([^"'`]{10,})\1''')
# An authored COMMENT is the single most recognisable thing in a file — upstream's
# "FIXME: race condition because sharedFolder doesn't use postie" survives any
# renaming. Length is the wrong filter for them: `// XXX file meta typing` is 23
# chars and unmistakably his. Any retained comment of >=3 words counts.
COMMENT = re.compile(r'^(//|/\*|\*(?!/)|<!--)\s*(.+)$')
# Language/framework incantations that are quoted literals but authored by nobody.
LITERAL_DENYLIST = frozenset({'"use strict";', "'use strict';", '"use client";'})


def substantive(line):
    s = line.strip()
    return len(s) >= 12 and not re.fullmatch(r'[\}\)\]\;\,\{\s]+', s)


def is_boilerplate(s):
    return any(p.match(s) for p in BOILERPLATE)


def distinguishable(s):
    if is_boilerplate(s) or s in LITERAL_DENYLIST:
        return False
    m = COMMENT.match(s)
    if m:
        return len(m.group(2).split()) >= 3
    return bool(LITERAL.search(s)) or len(s) >= 40


def read(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            return [l.strip() for l in fh.read().split('\n') if substantive(l)]
    except (FileNotFoundError, IsADirectoryError):
        return None


def bucket(rel):
    if rel in VENDOR_FILES:
        return 'vendor'
    if rel in DO_NOT_TOUCH:
        return 'do-not-touch'
    if rel in ADJUDICATED:
        return 'adjudicated'
    return 'in-scope'


def main():
    args = list(sys.argv[1:])
    cap = None
    samples_for = None
    out_json = None
    for flag, setter in (("--max-distinct", "cap"), ("--show-samples", "samples"),
                         ("--json", "json")):
        if flag in args:
            i = args.index(flag)
            val = args[i + 1]
            del args[i:i + 2]
            if setter == "cap":
                cap = int(val)
            elif setter == "samples":
                samples_for = val
            else:
                out_json = val
    if len(args) < 2:
        print(__doc__)
        return 2
    up_root, our_root = args[0], args[1]

    rows = []
    for root, _, names in os.walk(our_root):
        for n in sorted(names):
            if not n.endswith(('.ts', '.svelte', '.js')):
                continue
            po = os.path.join(root, n)
            rel = os.path.relpath(po, our_root).replace(os.sep, '/')
            u = read(os.path.join(up_root, rel))
            if u is None:
                continue
            o = read(po) or []
            keptc = Counter(u) & Counter(o)
            kept = sum(keptc.values())
            dist_lines = [l for l in keptc.elements() if distinguishable(l)]
            rows.append({"rel": rel, "bucket": bucket(rel), "upstream": len(u),
                         "kept": kept, "distinct": len(dist_lines),
                         "samples": sorted(set(dist_lines))[:5]})

    print(f"{'bucket':13s} {'files':>6s} {'kept':>7s} {'distinct':>9s}")
    for b in ('in-scope', 'adjudicated', 'do-not-touch', 'vendor'):
        sel = [r for r in rows if r['bucket'] == b]
        print(f"{b:13s} {len(sel):6d} {sum(r['kept'] for r in sel):7d} "
              f"{sum(r['distinct'] for r in sel):9d}")

    scope = sorted([r for r in rows if r['bucket'] == 'in-scope'],
                   key=lambda r: -r['distinct'])
    total = sum(r['distinct'] for r in scope)
    print(f"\nin-scope distinguishable total: {total} in "
          f"{sum(1 for r in scope if r['distinct'])} files")
    print(f"\n{'file':52s} {'kept':>5s} {'distinct':>8s}")
    for r in scope[:25]:
        print(f"{r['rel']:52s} {r['kept']:5d} {r['distinct']:8d}")
    top15 = sum(r['distinct'] for r in scope[:15])
    print(f"\ntop-15 files hold {top15}/{total} = {100.0*top15/total:.0f}% of the "
          f"distinguishable text" if total else "")

    if samples_for:
        r = next((x for x in rows if x['rel'] == samples_for), None)
        if not r:
            print(f"\n(no such file: {samples_for})")
        else:
            u = read(os.path.join(up_root, samples_for)) or []
            o = read(os.path.join(our_root, samples_for)) or []
            keptc = Counter(u) & Counter(o)
            print(f"\n--- {samples_for}: classified retained lines ---")
            print("DISTINGUISHABLE:")
            for l in sorted(set(l for l in keptc.elements() if distinguishable(l)))[:12]:
                print("   +", l[:110])
            print("DISCARDED as boilerplate/short:")
            for l in sorted(set(l for l in keptc.elements() if not distinguishable(l)))[:12]:
                print("   -", l[:110])

    over = [r for r in scope if cap is not None and r['distinct'] > cap]
    if cap is not None:
        print(f"\nfiles over --max-distinct {cap}: {len(over)}"
              f" (holding {sum(r['distinct'] for r in over)} lines)")
    if out_json:
        with open(out_json, 'w') as fh:
            json.dump(rows, fh, indent=1)
        print(f"per-file rows -> {out_json}")
    return 1 if over else 0


if __name__ == '__main__':
    sys.exit(main())
