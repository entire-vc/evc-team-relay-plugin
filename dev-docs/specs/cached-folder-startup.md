# Folder materialization after startup

An existing share's persisted Yjs state is an offline cache, not confirmation
that a path is still shared. On startup the cache can contain paths whose
deletions are already present on the server. The folder index must receive
the current connection's sync, including those deletions, before it migrates
legacy `docs` entries or creates missing vault folders/files.

The same prerequisite applies to automatic index observers and direct tree
scans. A previous `serverSynced` flag or historical provider sync does not
satisfy it. A timeout must not allow cached paths to create vault directories.
The initial prerequisite is shared by concurrent callers. After initialization,
normal online and offline tree processing remains available. A newly created
share is authoritative for its own initial paths and keeps its current offline
creation behavior; an existing share marked as authority by migration does not
receive that exception.

Existing vault content and cached document content are preserved while waiting.
No cache deletion, vault cleanup, private Obsidian API, server reset, or automatic
removal of user files is part of this startup change. Unloading a waiting share
must suppress all subsequent migration and filesystem work.

## Regression checks

- Restore a legacy cache containing `dev-docs/specs/old.md` and old folder
  metadata into a clean vault. Start a tree scan before delivering the server's
  deletion update: no path may be materialized or newly published. After sync,
  neither map may contain the deleted tree.
- Start the automatic index-observer lifecycle with the same old cache. An
  unrelated incoming update before fresh sync must not stage legacy parents.
- Deliver a live folder from the server: it must be materialized after sync.
- Delay sync past the startup timeout: cached folders must remain unmaterialized.
- Create a new share offline: its own initial folder processing remains usable.
- Unload before sync: resolving sync later must cause no filesystem work.

The public API and wire format are unchanged. Folders republished by an older
client are ordinary current records on the server; fixing startup does not
identify or remove those records. Removing a confirmed unwanted tree requires
the normal synchronized deletion workflow and a retained rollback snapshot.
