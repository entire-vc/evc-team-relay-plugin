#!/usr/bin/env python3
"""One-shot investigation for Mesh #a2f4027a: which of OUR classes are a
RENAMED upstream class, and what upstream name did they rename FROM?

check-naming.py's member axis only counts `Class.member` when BOTH trees
declare the exact same class name. Renaming a class silently removes its
entire member set from the comparison -- not because the members stopped
being upstream's vocabulary, but because the KEY vanished. This script
finds candidate (our_name -> upstream_name) pairs by structural similarity
(member-set overlap) between classes that exist in one tree but not the
other, so the predecessor mapping is MEASURED, not recalled from memory or
guessed from wave history.

Not the gate. A throwaway diagnostic that produces the PREDECESSOR_TYPES
table for check-naming.py -- each candidate below still needs a human
(or agent) to read both class bodies and confirm it is a real rename, not
a coincidental member-set overlap between two unrelated small classes.

Usage: find-renamed-class-predecessors.py <upstream_src> <our_src>
"""
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
# check-naming.py has a hyphen, not importable as a module name directly.
spec = importlib.util.spec_from_file_location('check_naming', os.path.join(HERE, 'check-naming.py'))
cn = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(cn)

# Names so generic that any two unrelated classes both having them tells you
# nothing about a rename relationship. Excluded from the similarity score
# entirely (not just discounted) so a pair of small unrelated classes that
# both merely have a constructor/destroy/log doesn't look like a match.
GENERIC_NOISE = {
    'constructor', 'destroy', 'log', 'warn', 'error', 'debug', 'info',
    'toString', 'toJSON', 'then', 'catch', 'finally', 'get', 'set',
    'subscribe', 'unsubscribe', 'on', 'off', 'load', 'unload',
}


def jaccard(a, b):
    a2, b2 = a - GENERIC_NOISE, b - GENERIC_NOISE
    if not a2 or not b2:
        return 0.0
    inter = len(a2 & b2)
    union = len(a2 | b2)
    return inter / union if union else 0.0


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    up_root, our_root = sys.argv[1], sys.argv[2]

    up_files, _ = cn.walk_tree(up_root)
    our_files, _ = cn.walk_tree(our_root)
    up_types, up_exports, up_members, _, _ = cn.collect(up_root, up_files)
    our_types, our_exports, our_members, our_bases, _ = cn.collect(our_root, our_files)

    up_only = set(up_members) - set(our_members)
    our_only = set(our_members) - set(up_members)

    print(f"upstream-only classes (candidates for 'predecessor'): {len(up_only)}")
    print(f"our-only classes (candidates for 'successor'):        {len(our_only)}")
    print()

    # Rank by RAW shared non-generic count, not the Jaccard ratio: a big
    # upstream class (e.g. LoginManager, 28 members) renamed into an even
    # bigger one of ours (AuthSession, 45 members -- it absorbed more
    # responsibility over 13 waves) scores a LOW ratio (0.25) despite being a
    # real, confirmed rename (per the task's own worked example) -- the ratio
    # is diluted by our side's own unrelated growth. The count of members that
    # ACTUALLY overlap is what matters for the gate; the ratio is only useful
    # as a tie-breaker among candidates with the same count.
    results = []
    for ours in sorted(our_only):
        our_set = set(our_members[ours])
        best = None
        for up in up_only:
            up_set = set(up_members[up])
            shared = (up_set & our_set) - GENERIC_NOISE
            if not shared:
                continue
            score = jaccard(our_set, up_set)
            key = (len(shared), score)
            if best is None or key > best[0]:
                best = (key, up, score, up_set, our_set, shared)
        if best and best[0][0] >= 3:
            _, up, score, up_set, our_set, shared = best
            results.append((ours, up, score, len(up_set), len(our_set), sorted(shared)))

    results.sort(key=lambda r: -len(r[5]))
    print(f"{'ours':24s} {'upstream':24s} {'shared':>6s} {'score':>6s} {'up#':>4s} {'our#':>5s}  shared (non-generic)")
    for ours, up, score, upn, ourn, shared in results:
        print(f"{ours:24s} {up:24s} {len(shared):6d} {score:6.2f} {upn:4d} {ourn:5d}  {shared}")

    print(f"\n{len(results)} candidate pairs at >=3 shared non-generic members (out of {len(our_only)} our-only classes)")


if __name__ == '__main__':
    sys.exit(main())
