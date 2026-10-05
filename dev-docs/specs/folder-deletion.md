# Shared folder deletion

Deleting a subfolder in a connected vault removes the folder and every path
below it from the shared folder index. Both `filemeta_v0` metadata and the
legacy `docs` map must receive the deletion in one Yjs transaction, including
empty folders and folders whose own metadata is absent. Paths that only share a
name prefix (for example `notes-old` when deleting `notes`) remain intact.

Pending deletion covers descendants while the share waits for readiness. Locally
staged metadata, pending identifiers, and tracked entries in the deleted tree
are discarded. Deferred metadata uploads from discarded entries must not
recreate the tree after the pending deletion ends. A later deliberate creation
at the same path is permitted with a new tracked entry.

Vault create events from a folder creation already in flight must wait for that
operation to settle before claiming a fresh identifier. When deletion discards
the originating entry, its returned folder object must not be uploaded. An empty
stale folder may be removed only if the vault still holds that exact object,
moving it to the vault’s local `.trash` through the public vault API. User-
created replacement objects and folders containing new user content must be
preserved. Missing ancestors are created separately, and ancestor create events
wait for a pending descendant operation if Obsidian recreates a parent during
recursive directory creation. New empty ancestors in that returned chain are
moved to local trash only when their original path lies inside the deleted
subtree. Deletion wins over an empty ancestor created during the still-running
discarded operation; once it settles, deliberate new creation is allowed.

Deleting the root of a share continues to detach that local share rather than
delete its remote contents. Wire schemas, REST endpoints, and MCP tool shapes
are unchanged; existing clients receive normal Yjs map deletions.

Cleanup does not permanently delete directories recursively. A folder already
containing user content is preserved in place. If content arrives after the
empty-folder check but before the trash operation, it remains recoverable in the
vault’s local `.trash` rather than being erased.
