#!/usr/bin/env python3
"""Gate 4 wave plan: turn the gate's row dump into the wave table and the
count of names still to decide.

Why this exists as a script and not as a number in a task comment: the
"names to decide" figure was retyped by hand twice while the tree moved
underneath it, and both times it came out unreproducible (once 478, once
436-labelled-as-the-pre-W1-tree). A planning number nobody can regenerate
is worse than no number — it gets quoted, and the quote outlives the tree
it was measured on. So the metric is executable, and its definition lives
next to the code it measures.

  ./scripts/check-naming.sh --show-samples /tmp/rows.tsv
  ./scripts/wave-plan.py /tmp/rows.tsv

Definition of a "name to decide" (pinned, so anyone can recompute it):

    union of { file basenames without extension }
            u { type names }
            u { export names }
            u { directory names }
    over the `work` basket only, deduplicated case-sensitively.

The dedup is load-bearing, not cosmetic: `Relay.ts` the file and `Relay`
the class inside it are ONE naming decision, not two. Members are excluded
by construction -- a `Class.member` row is only shared with upstream while
BOTH halves match, so renaming the owning type removes the whole member set
with it. Members ride along; they never need a decision of their own.

Exit 0 always: this reports, it does not gate. `check-naming.sh` is the gate.
"""
import collections
import csv
import sys

# Waves are cut by subsystem, not by size: a wave has to read as one story to
# a reviewer. Order runs periphery -> core, so the tooling is shaken out on a
# local diff before it touches SharedFolder (W6) and the root of src/ (W7).
W1_DIRS = {"notifiers", "observable", "utils"}   # observable/ was renamed to notifiers/ in W1
W2_DIRS = {"differ", "markdownView", "plugins"}
W5_FILES = {"S3RN.ts", "Relay.ts", "RelayManager.ts", "HasProvider.ts"}
W6_FILES = {
    "SharedFolder.ts", "SyncFile.ts", "SyncTypes.ts", "SyncStore.ts",
    "SyncFolder.ts", "BackgroundSync.ts", "Document.ts",
}
ORDER = ["W1", "W2", "W3", "W4", "W5", "W6", "W7"]

# W6 (440 rows) and W7 (653) are too large to read as one merge request -- the
# same objection that split the original 2002 into waves at all. They are cut by
# cohesion, not by size: each sub-wave has to read as one story to a reviewer.
# Sizes land between 71 and 225, the range already shipped without incident.
# Printed by --sub; the default table is unchanged so a wave in flight keeps
# measuring itself the same way.
SUBWAVES = {
    "W6a": ("sync vocabulary and store",
            {"SyncTypes.ts", "SyncStore.ts", "SyncFolder.ts", "SyncFile.ts"}),
    "W6b": ("the folder aggregate and its documents",
            {"SharedFolder.ts", "Document.ts"}),
    "W6c": ("background delivery",
            {"BackgroundSync.ts"}),
    "W7a": ("live views and editor plugins",
            {"LiveViews.ts", "TextViewPlugin.ts", "AwarenessViewPlugin.ts",
             "ShareLinkPlugin.ts", "Patcher.ts", "CanvasPlugin.ts",
             "CanvasView.ts", "Canvas.ts"}),
    "W7b": ("access, policy and tokens",
            {"CredentialCache.ts", "TenantRegistry.ts",
             "AuthSession.ts", "RelayCredentialCache.ts", "BlobClient.ts", "Account.ts"}),
    "W7c": ("settings, storage and flags",
            {"SettingsPersistence.ts", "AttachmentSyncSettings.ts", "featureToggleState.ts",
             "featureToggles.ts", "VaultScopedMap.ts", "StorageDiagnostics.ts"}),
    "W7d": ("infrastructure, utilities and the remainder",
            {"ServiceHealthMonitor.ts", "UnsavedFile.ts", "logging.ts", "Clock.ts",
             "ObsidianLogSinks.ts", "asyncCache.ts", "SyncableEntry.ts", "pathOrdering.ts",
             "deepValueEquals.ts", "rootRelativeProxy.ts",
             "platformFetch.ts", "ytextDiff.ts", "contentDigest.ts",
             "mimeLookup.ts", "inlineEmphasis.ts", "main.ts",
             "RelayOnPremShareClient.ts", "relay/TokenShapes.ts"}),
            # Renamed by gate4 W7d (#b2cf036c): every file above except
            # main.ts/RelayOnPremShareClient.ts/relay/TokenShapes.ts, which
            # keep their upstream-convergent or already-clean names. The
            # ghost entry "Frontmatter.ts" that used to sit here named a file
            # that no longer exists on disk (and never generated a row) --
            # dropped rather than carried forward, same cleanup class as the
            # dead check-verbatim-distinct.py ADJUDICATED/DO_NOT_TOUCH
            # entries from earlier waves.
}
LABEL = {
    "W1": "notifiers/ + utils/",
    "W2": "differ/ + markdownView/ + plugins/",
    "W3": "components/",
    "W4": "ui/",
    "W5": "core identity (S3RN, Relay, RelayManager, HasProvider)",
    "W6": "core sync (SharedFolder, SyncFile, SyncStore, Document, ...)",
    "W7": "rest of src/ root",
}


def module_of(axis, where):
    """Which module a row belongs to.

    The `dir` axis carries the module name in `where` WITHOUT a slash, so
    splitting on '/' returns None for it and silently dumps every directory
    rename into the catch-all wave. That bug put `observable/` in W7 while all
    of its files were in W1 -- and the totals still added up, which is exactly
    why it survived a read-through. Handle the dir axis first.
    """
    if axis == "dir":
        return where
    return where.split("/")[0] if "/" in where else None


def wave_of(axis, where):
    mod = module_of(axis, where)
    if mod is None:                       # a file at the root of src/
        if where in W5_FILES:
            return "W5"
        if where in W6_FILES:
            return "W6"
        return "W7"
    if mod in W1_DIRS:
        return "W1"
    if mod in W2_DIRS:
        return "W2"
    if mod == "components":
        return "W3"
    if mod == "ui":
        return "W4"
    return "W7"


def subwave_of(where):
    """Which sub-wave a W6/W7 row belongs to, or None."""
    for key, (_label, files) in SUBWAVES.items():
        if where in files:
            return key
    return None


def report_subwaves(work):
    """Break W6 and W7 down, and refuse to look tidy if a row has no home."""
    rows = [r for r in work if wave_of(r[1], r[3]) in ("W6", "W7")]
    counts, names, homeless = collections.Counter(), collections.defaultdict(set), []
    for _cat, axis, name, where in rows:
        key = subwave_of(where)
        if key is None:
            homeless.append((axis, name, where))
            continue
        counts[key] += 1
        if axis == "file":
            names[key].add(name.rsplit("/", 1)[-1].rsplit(".", 1)[0])
        elif axis in ("type", "export", "dir"):
            names[key].add(name)

    print(f"\n{'sub-wave':6} {'rows':>5} {'names':>6}  subsystem")
    for key, (label, _f) in SUBWAVES.items():
        # Done means no NAME left to decide, not zero rows (docstring above:
        # "Members ride along; they never need a decision of their own"). A
        # sub-wave whose file carries a CONVERGENT type (Document.ts, W6b)
        # keeps permanent member-axis residue after its one real decision
        # (isDocument) is made -- that type's name is never getting renamed,
        # so those rows can never reach zero under ANY future wave. Gating
        # "(done)" on counts[key] would leave such a sub-wave red forever for
        # a decision that is, in fact, complete. Found live on W6b: rows=51,
        # names=0 the moment isDocument moved to convergent (#bb92da57).
        state = "" if names[key] else "   (done)"
        print(f"{key:6} {counts[key]:5} {len(names[key]):6}  {label}{state}")
    print(f"{'TOTAL':6} {sum(counts.values()):5}")

    # A row with no sub-wave would leave real work invisible while the table
    # still adds up against W6+W7. Unlike the wave-level guard this one CAN
    # fire in normal use -- a new root-level file belongs to no sub-wave until
    # someone puts it in one.
    if homeless:
        print(f"\nFATAL: {len(homeless)} W6/W7 rows belong to no sub-wave "
              f"(a new file needs a home in SUBWAVES):", file=sys.stderr)
        for axis, name, where in homeless[:10]:
            print(f"    {axis:7} {name:28} [{where}]", file=sys.stderr)
        return 2
    return 0


def main(path, want_sub=False):
    with open(path, newline="") as fh:
        rows = [r for r in csv.reader(fh, delimiter="\t") if r]

    work = [r for r in rows if r[0] == "work"]
    per_axis = collections.defaultdict(collections.Counter)
    names = collections.defaultdict(set)
    total = collections.Counter()
    every_name = []          # row-level, pre-dedup -- so "collapsed" is honest

    for _cat, axis, name, where in work:
        w = wave_of(axis, where)
        total[w] += 1
        per_axis[w][axis] += 1
        if axis == "file":
            # basename only: `ui/Banner.svelte` and `class Banner` are ONE
            # decision -- rename the class and the file follows it. Keeping the
            # directory prefix here counts that pair twice and inflates the
            # figure by 16 on this tree.
            plain = name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            names[w].add(plain)
            every_name.append(plain)
        elif axis in ("type", "export", "dir"):
            names[w].add(name)
            every_name.append(name)

    print(f"{'wave':5} {'rows':>5} {'file':>5} {'dir':>4} {'type':>5} "
          f"{'member':>7} {'export':>7} {'names':>6}  subsystem")
    for w in ORDER:
        a = per_axis[w]
        # See the matching comment in report_subwaves: done means no NAME
        # left, not zero rows -- a permanently-convergent file's member
        # residue (Document.ts, in W6) never reaches zero row-count on its
        # own and would otherwise pin the whole wave un-done forever.
        state = "" if names[w] else "   (done)"
        print(f"{w:5} {total[w]:5} {a['file']:5} {a['dir']:4} {a['type']:5} "
              f"{a['member']:7} {a['export']:7} {len(names[w]):6}  {LABEL[w]}{state}")

    union = set(every_name)
    raw = len(every_name)
    print(f"{'TOTAL':5} {sum(total.values()):5}")
    print(f"\nwork basket rows      : {sum(total.values())}")
    print(f"names to decide       : {len(union)}"
          f"   (raw {raw} rows on the naming axes, "
          f"{raw - len(union)} collapsed as duplicate names)")

    # A row assigned to no wave would make the table add up while hiding work.
    # Sum over ORDER only -- summing total.values() would silently include an
    # unknown label and make this guard unable to fail, which is how the first
    # version of it shipped. Verified by breaking wave_of on purpose.
    placed = sum(total[w] for w in ORDER)
    if placed != len(work):
        stray = collections.Counter(
            w for w in total if w not in ORDER)
        print(f"\nFATAL: {len(work) - placed} work rows fell outside every "
              f"wave (labels: {sorted(stray) or 'none'})", file=sys.stderr)
        return 2
    if want_sub:
        return report_subwaves(work)
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--sub"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], want_sub="--sub" in sys.argv[1:]))
