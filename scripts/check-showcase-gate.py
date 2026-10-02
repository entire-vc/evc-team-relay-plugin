#!/usr/bin/env python3
"""Showcase-publisher content gate, run in the MR pipeline (#c268f8f8).

WHY. The public showcase is cut from this repository by a publisher
(tr-showcase-publish.py, on the GitLab VM) whose content gate is fail-closed:
if the tree it is about to publish contains a forbidden pattern, it silently
publishes NOTHING. On 2026-09-19 that held release 0.0.13 back for ~40 minutes:
a test comment said "upstream" (meaning the Yjs library), the MR pipeline was
green, the merge was clean, and the only place the refusal showed was the
publisher, after the merge. This script runs the SAME check before the merge.

WHAT IT SCANS. Exactly what the publisher scans: the tracked files that pass
the publisher's allow-list (`_is_publishable`: ALLOW_PREFIXES / ALLOW_FILES),
their PATHS and their CONTENT, line by line, against the publisher's FORBIDDEN
patterns. Anything outside the allow-list (scripts/, .gitlab-ci.yml, ...) is
never published, so it is never scanned: this very file spells every pattern
out and is not a finding.

NOT SCANNED, ON PURPOSE: commit messages of the MR. The publisher does not
publish them: it commits the tree with a FIXED template message (see
`SNAPSHOT_MESSAGE_TEMPLATE`), and canon commit objects never reach the
showcase. Scanning them here would fail MRs the publisher would accept. The
fixed template itself is checked by --self-test.

THE PATTERNS ARE A COPY. The block between the SYNC markers below is copied
from the private showcase publisher (tr-showcase-publish.py) (FORBIDDEN, NEGATIVE_CANARY,
ALLOW_PREFIXES, ALLOW_FILES) -- generated from the publisher's AST, not typed.
A copy can drift, and a drifted copy gives a false green, so:

    python3 scripts/check-showcase-gate.py --compare-with <path to tr-showcase-publish.py>

diffs the four values against the publisher and exits 1 on any difference. Run
it whenever the publisher changes (its owner) and whenever this block is
touched. CI cannot run it: the publisher lives outside this repository.

Copy last synced 2026-09-19 from publisher sha256
be48f390543044a907147f66d28653f1ee7e3db7fe0d75a5f50dff876e27877d
(identical to the copy deployed at the canon host).

USAGE
    check-showcase-gate.py              scan the tracked tree (exit 1 on findings,
                                        2 if the check could not be performed)
    check-showcase-gate.py --self-test  prove the gate goes red on each pattern
                                        and stays green on clean text
    check-showcase-gate.py --compare-with PUBLISHER.py
"""
import argparse
import ast
import os
import re
import subprocess
import sys

# --- SYNC BEGIN: copied from tr-showcase-publish.py -----------------------

FORBIDDEN = [
    ('upstream-lineage',
     'upstream',
     'cloned from the upstream repo'),
    ('no-instructions',
     'no[-_\\s]?instructions',
     'no-instructions/relay and No Instructions, LLC'),
    ('dtkav',
     'dtkav',
     'github.com/dtkav/relay'),
    ('system3',
     'system[-_\\s]?3\\b',
     'Copyright System3'),
    ('derivativeness',
     'derivativ',
     'a derivativeness baseline has no business here'),
    ('fork-point',
     'fork[-_.\\s]?point',
     'read the fork-point out of the script'),
    ('fork-point-sha',
     'd1b24af2',
     'FORK_POINT="d1b24af2"'),
    ('copied-verbatim',
     'copied\\s+verbatim|verbatim\\s+from|byte[-\\s]for[-\\s]byte\\s+identical',
     'design copied verbatim from the original'),
    ('internal-tracker',
     'mesh\\s*#\\s*[0-9a-f]{6,}',
     'see Mesh #ba5e25dd for the reasoning'),
]

NEGATIVE_CANARY = 'A plain Obsidian plugin: syncs a folder between devices, shows a status bar, and never phones home.'

ALLOW_PREFIXES = (
    'src/',
    '__tests__/',
    '.github/ISSUE_TEMPLATE/',
)

ALLOW_FILES = frozenset({
    '.editorconfig',
    '.github/PULL_REQUEST_TEMPLATE.md',
    '.github/workflows/ci.yml',
    '.github/workflows/release.yml',
    '.gitignore',
    '.npmrc',
    '.prettierrc',
    'CHANGELOG.md',
    'CODE_OF_CONDUCT.md',
    'CONTRIBUTING.md',
    'LICENSE',
    'NOTICE',
    'README.md',
    'SECURITY.md',
    'SUPPORT.md',
    'beta-version.py',
    'esbuild.config.mjs',
    'eslint.config.bot.mjs',
    'eslint.config.mjs',
    'icon.svg',
    'jest.config.js',
    'jest.live.config.js',
    'manifest-beta.json',
    'manifest.json',
    'package-lock.json',
    'package.json',
    'styles.css',
    'svelte.config.mjs',
    'tsconfig.json',
    'tsconfig.svelte-check.json',
    'tsconfig.tests.json',
    'version-bump.mjs',
    'version.py',
    'versions.json',
})

# --- SYNC END --------------------------------------------------------------

# The publisher's own commit message is this fixed template; only the date and
# the tree hash vary. Copied from its `commit_msg = (...)`.
SNAPSHOT_MESSAGE_TEMPLATE = "Publish snapshot (%s)\n\nSource tree %s.\n"


def is_publishable(path):
    return path in ALLOW_FILES or any(path.startswith(p) for p in ALLOW_PREFIXES)


def compile_patterns():
    """Compile every pattern and prove it against its own canary and the
    negative canary. A broken regex would otherwise give zero findings, which
    reads exactly like a clean tree."""
    if not FORBIDDEN:
        raise RuntimeError("pattern list is empty - refusing to check blind")
    out = []
    for name, raw, canary in FORBIDDEN:
        try:
            rx = re.compile(raw, re.IGNORECASE)
        except re.error as e:
            raise RuntimeError("pattern %r does not compile: %s" % (name, e))
        if not rx.search(canary):
            raise RuntimeError(
                "pattern %r does not match its own canary %r - the regex is "
                "broken, zero hits would mean nothing" % (name, canary))
        if rx.search(NEGATIVE_CANARY):
            raise RuntimeError(
                "pattern %r fires on known-clean text - the gate would reject "
                "everything" % name)
        out.append((name, rx))
    return out


def scan(blobs):
    """blobs: iterable of (path, bytes). Same shape as the publisher's
    `content_gate`: a path check, then a per-line check, per pattern, only for
    publishable paths. Returns (findings, files_scanned, patterns_used)."""
    pats = compile_patterns()
    findings, scanned = [], 0
    for path, body in blobs:
        if not is_publishable(path):
            continue
        scanned += 1
        text = body.decode("utf-8", "replace")
        for name, rx in pats:
            if rx.search(path):
                findings.append("[%s] FILE NAME: %s" % (name, path))
            for i, ln in enumerate(text.splitlines(), 1):
                if rx.search(ln):
                    findings.append("[%s] %s:%d: %s" % (name, path, i, ln.strip()[:200]))
    return findings, scanned, len(pats)


def tracked_blobs():
    """(path, bytes) for every tracked file. An empty or unreadable tree raises:
    "could not check" must never look like "checked, clean"."""
    r = subprocess.run(["git", "ls-files", "-z", "--stage"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git ls-files failed: %s" % r.stderr.decode("utf-8", "replace")[:200])
    paths = []
    for rec in r.stdout.decode("utf-8", "replace").split("\0"):
        if not rec:
            continue
        meta, _, path = rec.partition("\t")
        parts = meta.split()
        if len(parts) != 3 or not path:
            raise RuntimeError("cannot parse ls-files record %r" % rec[:120])
        if parts[0] == "160000":
            raise RuntimeError("submodule %r in the tree - cannot check its content" % path)
        paths.append(path)
    if not paths:
        raise RuntimeError("git ls-files returned no files - cannot read the tree")
    blobs = []
    for path in paths:
        try:
            if os.path.islink(path):
                # git stores a symlink's blob as the link target text, and that
                # is what the publisher scans; open() would follow the link.
                blobs.append((path, os.readlink(path).encode("utf-8", "surrogateescape")))
                continue
            with open(path, "rb") as f:
                blobs.append((path, f.read()))
        except OSError as e:
            raise RuntimeError("cannot read tracked file %r: %s" % (path, e))
    return blobs


def self_test():
    """Red on every pattern through the real scan path, green on clean text,
    blind to files the publisher never ships."""
    failures = []
    pats = compile_patterns()  # own canaries + negative canary
    for name, _raw, canary in FORBIDDEN:
        hits, _n, _p = scan([("src/probe.ts", ("// " + canary + "\n").encode())])
        named = [h for h in hits if h.startswith("[%s]" % name)]
        if not named:
            failures.append("pattern %r did not go red on its canary in src/" % name)
        elif "src/probe.ts:1:" not in named[0]:
            failures.append("finding for %r lacks path:line: %r" % (name, named[0]))
        if scan([("scripts/probe.ts", canary.encode())])[0]:
            failures.append("pattern %r fired on a path the publisher never ships" % name)
    hits, _n, _p = scan([("src/clean.ts", NEGATIVE_CANARY.encode())])
    if hits:
        failures.append("clean text produced findings: %r" % hits[:3])
    hits, _n, _p = scan([("src/upstream-notes.ts", b"export const a = 1;\n")])
    if not any("FILE NAME" in h for h in hits):
        failures.append("a forbidden word in a publishable FILE NAME was not caught")
    if scan([("not-published.txt", b"upstream\n")])[0]:
        failures.append("a file outside the allow-list was scanned")
    if scan([])[1] != 0:
        failures.append("empty input should scan zero files")
    msg = (SNAPSHOT_MESSAGE_TEMPLATE % ("2026-01-01", "0123456789ab")).encode()
    if scan([("src/msg.txt", msg)])[0]:
        failures.append("the publisher's own commit-message template trips the gate")
    if failures:
        for f in failures:
            print("SELF-TEST FAIL: " + f)
        return 1
    print("self-test OK: %d patterns each red on their canary (path:line reported), green on "
          "clean text, blind to unpublished paths, file-name check works" % len(pats))
    return 0


def _normalise(name, value):
    if name == "FORBIDDEN":
        return [tuple(t) for t in value]
    if name == "ALLOW_PREFIXES":
        return tuple(value)
    if name == "ALLOW_FILES":
        return frozenset(value)
    return value


def compare_with(publisher_path):
    """Diff the four copied values against the publisher's source, parsed with
    ast (never executed)."""
    with open(publisher_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    theirs = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n = node.targets[0].id
            if n in ("FORBIDDEN", "NEGATIVE_CANARY", "ALLOW_PREFIXES"):
                theirs[n] = ast.literal_eval(node.value)
            elif n == "ALLOW_FILES":
                theirs[n] = ast.literal_eval(node.value.args[0])
    ours = {"FORBIDDEN": FORBIDDEN, "NEGATIVE_CANARY": NEGATIVE_CANARY,
            "ALLOW_PREFIXES": ALLOW_PREFIXES, "ALLOW_FILES": ALLOW_FILES}
    bad = 0
    for k, v in ours.items():
        if k not in theirs:
            print("DRIFT: %s not found in %s (renamed? this comparison is blind until fixed)" % (k, publisher_path))
            bad += 1
        elif _normalise(k, theirs[k]) != _normalise(k, v):
            print("DRIFT: %s differs from the publisher" % k)
            bad += 1
    if bad:
        return 1
    print("in sync with %s (FORBIDDEN, NEGATIVE_CANARY, ALLOW_PREFIXES, ALLOW_FILES)" % publisher_path)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Showcase-publisher content gate")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--compare-with", metavar="PUBLISHER.py")
    args = ap.parse_args()
    # A finding line can carry any character from a source file; never let a
    # non-UTF-8 stdout turn "findings" into a UnicodeEncodeError traceback.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    try:
        if args.self_test:
            return self_test()
        if args.compare_with:
            return compare_with(args.compare_with)
        findings, scanned, npat = scan(tracked_blobs())
    except RuntimeError as e:
        print("REFUSING: could not perform the check - %s" % e)
        return 2
    if scanned == 0:
        print("REFUSING: no tracked file passed the publisher allow-list - the list and the "
              "tree have drifted apart, nothing was checked")
        return 2
    print("showcase gate: %d patterns (each proven on its canary), %d publishable files scanned, "
          "findings: %d" % (npat, scanned, len(findings)))
    for f in findings:
        print("  " + f)
    if findings:
        print("The publisher would refuse to publish this tree and the release would stall "
              "silently after the merge. Reword the lines above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
