# Folder deletion verification

The same behavioral fixture reproduces incomplete shared-folder deletion in both published source versions. The fix removes the subtree from `filemeta_v0` and legacy `docs`, suppresses delayed writes, and preserves paths outside the deleted subtree. Verification was recorded on 2026-10-05.

## Source provenance

Public repository: [entire-vc/evc-team-relay-plugin](https://github.com/entire-vc/evc-team-relay-plugin).

| Version | Source revision | Result |
| --- | --- | --- |
| `0.0.3` | `06b2f0ca730ca6f016462c6834df30e231c4e46a` | 8 failing behavioral assertions, 1 passing positive control |
| `0.0.26` | `f941fbd0584c9fda9a1c802e9096aa614ba7d1a2` | 8 failing behavioral assertions, 1 passing positive control |
| Initial subtree fix, manifest `0.0.27` | `5c0bd4fd34f0d72f556f728b82d39caa54c5568a` | 9 passing deletion tests; 47 passing tests with FolderIndex regression coverage |

The verification fixture includes realistic asynchronous folder creation and a share root path. Its historical failures are assertion failures, with no `TypeError`. The fixture SHA256 is:

```text
e86d6cafad6fed8efbdecd67fa07669f8c8f52c22bd425b00ddaed377ead1644  __tests__/folderDeletion.test.ts
```

The fix revision identifies the initial subtree-deletion code. The fixture adjustments, deferred-creation follow-up, and this verification note follow it in the same change; the separate race comparison is documented below.

## Reproduce the source comparison

Run from the fixed checkout with Node.js and npm installed. This uses the fixed checkout's dependency tree and Jest configuration for both historical source trees, so dependency/configuration changes do not account for the red/green result. The historical source trees retain their own Jest setup and Obsidian mocks.

```sh
npm ci
repo_root=$(pwd)
probe_dir=$(mktemp -d)
shasum -a 256 __tests__/folderDeletion.test.ts
git ls-remote https://github.com/entire-vc/evc-team-relay-plugin.git refs/tags/0.0.3 refs/tags/0.0.26

for revision in 06b2f0ca730ca6f016462c6834df30e231c4e46a f941fbd0584c9fda9a1c802e9096aa614ba7d1a2; do
  mkdir "$probe_dir/$revision"
  curl --fail --location --silent --show-error \
    "https://api.github.com/repos/entire-vc/evc-team-relay-plugin/tarball/$revision" \
    -o "$probe_dir/$revision.tar.gz"
  tar -xzf "$probe_dir/$revision.tar.gz" --strip-components=1 -C "$probe_dir/$revision"
  ln -s "$repo_root/node_modules" "$probe_dir/$revision/node_modules"
  cp "$repo_root/__tests__/folderDeletion.test.ts" "$probe_dir/$revision/__tests__/folderDeletion.test.ts"
  cp "$repo_root/jest.config.js" "$probe_dir/$revision/jest.config.js"
  (cd "$probe_dir/$revision" && ./node_modules/.bin/jest __tests__/folderDeletion.test.ts --runInBand) \
    > "$probe_dir/$revision-red.txt" 2>&1
  result=$?
  cat "$probe_dir/$revision-red.txt"
  test "$result" -eq 1 || exit 1
done

npx jest __tests__/folderDeletion.test.ts __tests__/TestFolderIndex.ts --runInBand
```

Each historical run exits 1 with this result:

```text
Test Suites: 1 failed, 1 total
Tests:       8 failed, 1 passed, 9 total
```

Both versions leave an empty nested folder on the synced peer after deleting its parent:

```text
shared subfolder deletion › empty-tree tree is deleted on a synced peer and stays deleted after migration
expect(received).toEqual(expected) // deep equality
- Array []
+ Array [
+   "notes/nested",
+ ]
```

A lone empty folder already passes on both historical versions. The failing empty-folder case is a parent with an empty nested subtree. Populated and legacy-only subtrees also fail. The remaining assertions cover pending descendant writes, staged metadata, delayed folder creation/upload, and single-file staged metadata cleanup.

The fixed checkout exits 0:

```text
Test Suites: 2 passed, 2 total
Tests:       47 passed, 47 total
Snapshots:   0 total
```

## Real relay transport check

An isolated relay-server `1.13.0` was exercised with two independent Yjs WebSocket clients and BroadcastChannel disabled. The source-version `0.0.26` baseline has the same `VaultShare.ts` SHA256 as the published `0.0.26` tag (`149afaa572af4f1b3db9ec334743745e6f825d793d9a7e4928102cbd6da5ac35`). The positive control first observed the populated subtree on the second client. After deletion, the baseline retained these legacy keys:

```text
- Array []
+ Array [
+   "notes/nested/a.md",
+   "notes/legacy.md",
+ ]
Test Suites: 1 failed, 1 total
Tests:       1 failed, 1 total
```

The fixed transport probe also decoded `GET /d/<document-id>/as-update` into a fresh Y.Doc, then restarted the isolated relay and checked another decoded update. It asserted content in both maps, including preservation of `notes-old/keep.md` and `outside.md`:

```text
PASS: peer subtree removed in both maps; legacy migration does not resurrect it; prefix sibling survives
PASS: real relay HTTP as-update contains deletions in both maps
PASS: relay restart preserves subtree deletion and positive controls
Test Suites: 1 passed, 1 total
Tests:       1 passed, 1 total
```

## Running Obsidian check

Published `0.0.3` and `0.0.26` bundles and the fixed `0.0.27` bundle were loaded separately in an isolated Obsidian vault. Each run created a local share with `shareRegistry.new(root, id, undefined, false)` and awaited readiness. The fixture contained `notes/nested/a.md`, `notes-old/keep.md`, and a lone empty folder. It then injected `notes/remote-empty` into `filemeta_v0` without creating that directory on disk, simulating stale remote folder metadata. It deleted `notes` and the lone empty folder through `app.vault.delete(folder, true)`, exercising the normal vault delete events, and inspected the loaded vault paths and both CRDT maps after synchronization settled.

Both historical bundles recreated `notes/remote-empty` and its parent on disk. The following fields are identical except for the version/root name; UUIDs and unrelated diagnostic fields are omitted:

```json
{
  "version": "0.0.3",
  "local": ["Probe-0.0.3", "Probe-0.0.3/notes-old", "Probe-0.0.3/notes-old/keep.md", "Probe-0.0.3/notes", "Probe-0.0.3/notes/remote-empty"],
  "meta": ["notes", "notes-old", "notes-old/keep.md", "notes/remote-empty"],
  "docs": []
}
```

```json
{
  "version": "0.0.26",
  "local": ["Probe-0.0.26", "Probe-0.0.26/notes-old", "Probe-0.0.26/notes-old/keep.md", "Probe-0.0.26/notes", "Probe-0.0.26/notes/remote-empty"],
  "meta": ["notes", "notes-old", "notes-old/keep.md", "notes/remote-empty"],
  "docs": []
}
```

Both historical runs end with `AssertionError: DELETED SUBTREE SURVIVES CRDT`. The fixed run preserves the sibling and removes the deleted paths from disk and both maps:

```json
{
  "version": "0.0.27",
  "local": ["Probe-0.0.27", "Probe-0.0.27/notes-old", "Probe-0.0.27/notes-old/keep.md"],
  "meta": ["notes-old", "notes-old/keep.md"],
  "docs": []
}
```

```text
PASS: real Obsidian delete events remove disk and metadata, including metadata-only empty folder; sibling preserved
```

These app and relay checks used isolated fixtures and did not modify an existing shared vault or production service.

## Deferred folder creation race

A separate regression fixture, `__tests__/folderCreationRace.test.ts`, exercises the actual `claimAndUploadFile` entry point used by the normal vault create handler. Before the race fix, a paused folder creation resumed after `markDeletePending`, `removeEntry`, and `clearDeletePending`, and the resulting create event minted fresh metadata. The first three-case regression run recorded:

```text
Expected: false
Received: true
Test Suites: 1 failed, 1 total
Tests:       2 failed, 1 passed, 3 total
```

Adding a nested-child case also demonstrated that creating ancestors separately is insufficient when an existing ancestor disappears during the child operation:

```text
Test Suites: 1 failed, 1 total
Tests:       1 failed, 4 passed, 5 total
```

The running Obsidian bundle built before the race fix reproduced both failures. The probe paused `app.vault.createFolder` for the tracked path, deleted the entry/subtree and cleared its pending flag, then resumed the original vault API. The normal create handler ran without intervention. Root names below are normalized to `<probe-root>`; map keys are unchanged.

```json
{
  "version": "0.0.27",
  "local": ["<probe-root>", "<probe-root>/late"],
  "meta": ["late"],
  "docs": []
}
```

```json
{
  "version": "0.0.27",
  "local": ["<probe-root>", "<probe-root>/late", "<probe-root>/late/nested"],
  "meta": ["late/nested", "late"],
  "docs": []
}
```

Both app runs recorded `AssertionError: LATE CREATE RECREATED DELETED FOLDER`.

An intermediate app check showed that desktop `vault.delete(folder, false)` throws `ERR_FS_EISDIR` even for an empty directory. The cleanup therefore uses the supported local-trash API.

The fix registers folder operations before invoking the vault API, defers matching ancestor create events through pending descendant operations, and snapshots the returned parent chain before any cleanup. It removes only currently-held empty objects from the discarded operation inside the deleted subtree, bottom-up through `vault.trash(node, false)` into the vault’s local `.trash`. Existing ancestors, replacement objects outside that chain, and folders containing new user content are preserved. Deletion wins over an empty ancestor created during the still-running discarded descendant operation; deliberate recreation after that operation settles is permitted. Constructor cancellation/rejection is handled without an unhandled rejection. Content arriving after the empty check remains recoverable in local trash; cleanup never uses permanent recursive deletion.

Run the expanded source check from the fixed checkout:

```sh
npx jest __tests__/folderCreationRace.test.ts __tests__/folderDeletion.test.ts __tests__/TestFolderIndex.ts --runInBand
```

Recorded source result (including synchronous-create/deadlock, nested creation, replacement-object, user-content, and post-settlement recreation controls):

```text
Test Suites: 3 passed, 3 total
Tests:       55 passed, 55 total
Snapshots:   0 total
```

The final running Obsidian check repeated both paused leaf and nested operations
with the local-trash cleanup. Both runs recorded the following fields, with
root names normalized to `<probe-root>`:

```json
{
  "version": "0.0.27",
  "warnings": [],
  "deletedEntry": true,
  "deletedRoot": "late",
  "local": ["<probe-root>"],
  "meta": [],
  "docs": []
}
```

```text
PASS: actual vault create event does not republish a delayed deleted folder
```

A separate running-app control inserted `recover.md` after the empty-folder
check, immediately before the original `app.vault.trash` call. The shared maps
remained empty and the active vault contained only the share root. The content
marker was found exactly once in the vault's local trash:

```text
PASS: content added after empty check preserved in vault/.trash/late 3/recover.md
```

The original historical fixture and its SHA256 remain unchanged.
