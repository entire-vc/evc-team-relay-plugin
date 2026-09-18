"use strict";

import { TFolder, type Vault } from "obsidian";

/**
 * Obsidian's own vault root `TFolder` reports `.path === "/"` -- but the
 * relay wire protocol (and this plugin's internal `VaultShare.path`)
 * represents "the whole vault" as the empty string `""`, matching the
 * convention every other folder path already follows (never a leading
 * slash). This is the single place that translates between the two, so the
 * folder-picker UI (which reads real `TFolder.path` values) and the
 * share/VaultShare layer (which expects the wire convention) don't drift
 * out of sync with each other.
 */
export const OBSIDIAN_VAULT_ROOT_PATH = "/";

/** True if `path` is the wire/internal representation of the vault root. */
export function isRootSharePath(path: string): boolean {
	return path === "";
}

/**
 * Converts a path as reported by the Obsidian API (e.g. `TFolder.path`,
 * which is `"/"` for the vault root) into the wire/internal share-path
 * convention (`""` for the vault root, unchanged otherwise).
 */
export function toSharePath(obsidianPath: string): string {
	return obsidianPath === OBSIDIAN_VAULT_ROOT_PATH ? "" : obsidianPath;
}

/**
 * Resolves the on-disk `TFolder` a share's `.path` points at, honoring the
 * vault-root convention above.
 *
 * A naive `vault.getAbstractFileByPath(share.path)` breaks for root shares:
 * `share.path` is `""` (the wire convention), but Obsidian's real root
 * `TFolder.path` is `"/"` (`OBSIDIAN_VAULT_ROOT_PATH`) -- so the lookup finds
 * nothing and callers that don't check for that treat the share as if its
 * backing folder doesn't exist (adoption/full-sync/prune of a root share
 * silently no-ops or throws). `vault.getRoot()` is Obsidian's own documented
 * way to get the root `TFolder` without relying on path lookup at all --
 * every call site that needs "the TFolder a share's `.path` points at" should
 * go through this helper instead of `getAbstractFileByPath` directly.
 */
export function resolveShareFolder(vault: Vault, sharePath: string): TFolder | null {
	if (isRootSharePath(sharePath)) {
		return vault.getRoot();
	}
	const abstractFile = vault.getAbstractFileByPath(sharePath);
	return abstractFile instanceof TFolder ? abstractFile : null;
}
