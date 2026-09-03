#!/usr/bin/env python3
"""Inventory of the strings a USER reads, for src/components/ and src/ui/.

Exists to make one acceptance criterion checkable instead of assertable: the
UI rewrite (Mesh #4d55aa42) may rewrite markup, structure and class names
freely, but every user-visible string must survive VERBATIM, because product
copy changes only with Pavel's approval (CLAUDE-workflow §1r.A).

"I didn't change any text" is not evidence. This turns it into a diff:

    ./scripts/extract-user-strings.py > before.txt   # on the base commit
    ./scripts/extract-user-strings.py > after.txt    # after the rewrite
    diff before.txt after.txt                        # must be empty

Deliberately NOT collected, because §1r.A leaves them ungated and the rewrite
is expected to change them: aria-label, title=, alt, CSS classes, ids, imports,
and anything that never reaches the screen as prose.

Over-collection is the safer failure here: a false positive costs one look at a
diff line, a false negative silently ships changed product copy.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCOPE = ["src/components", "src/ui"]

# Obsidian/Svelte APIs whose argument is rendered to the user as prose.
CALLS = r"(?:setName|setDesc|setButtonText|setPlaceholder|setText|setTitle|Notice|confirm|setMessage|addButton|setLabel)"
CALL_RE = re.compile(CALLS + r"\s*\(\s*([\"'`])(.*?)(?<!\\)\1", re.S)

# Text nodes in Svelte markup: prose sitting between tags. Requires a letter so
# that punctuation, whitespace and `{expr}` interpolation don't register.
TEXT_RE = re.compile(r">([^<>{}]*[A-Za-z][^<>{}]*)<")

# placeholder="..." is read by the user; title=/aria-label= are not gated.
ATTR_RE = re.compile(r"\bplaceholder\s*=\s*([\"'])(.*?)\1")

NOISE = re.compile(r"^[\s\W\d]*$")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def block_re(tag: str) -> "re.Pattern[str]":
    """
    Matches a whole <tag>…</tag> block, ending at any closing tag an HTML
    parser would accept: `</script>`, `</script >`, even `</script\t\n foo>` —
    junk is permitted between the tag name and the `>`. The lookahead keeps
    that tolerance from swallowing a longer word, so `</scriptural>` is not
    read as a script end tag. (CodeQL py/bad-tag-filter.)

    Getting this wrong is not cosmetic here: a block that survives stripping
    puts every string literal inside it into the extraction, which either
    fabricates a copy diff or buries a real one — and that diff is the whole
    evidence for "no user-visible text changed".
    """
    return re.compile(rf"<{tag}.*?</{tag}(?=[\s/>])[^>]*>", re.S | re.I)


SCRIPT_RE = block_re("script")
STYLE_RE = block_re("style")


def strip_block(text: str, tag: str) -> str:
    return (SCRIPT_RE if tag == "script" else STYLE_RE).sub("", text)


def harvest(path: pathlib.Path):
    src = path.read_text(encoding="utf-8", errors="replace")
    out = set()
    for m in CALL_RE.finditer(src):
        out.add(clean(m.group(2)))
    for m in ATTR_RE.finditer(src):
        out.add(clean(m.group(2)))
    if path.suffix == ".svelte":
        # Only the markup half: a <script> block's string literals are logic,
        # and including them would flood the diff with non-prose churn.
        markup = strip_block(src, "script")
        markup = strip_block(markup, "style")
        for m in TEXT_RE.finditer(markup):
            out.add(clean(m.group(1)))
    return {s for s in out if s and not NOISE.match(s) and len(s) > 1}


def main():
    strings = set()
    files = 0
    for d in SCOPE:
        for p in sorted((ROOT / d).rglob("*")):
            if p.suffix in (".svelte", ".ts") and p.is_file():
                files += 1
                strings |= harvest(p)
    # Sorted, file-agnostic: moving a string between files is a refactor, not a
    # copy change, and must not show up as one.
    for s in sorted(strings):
        print(s)
    print(f"# {len(strings)} distinct user-visible strings across {files} files", file=sys.stderr)


if __name__ == "__main__":
    main()
