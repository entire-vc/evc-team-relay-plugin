"use strict";

/**
 * Recognises a path move the server committed while this client was offline.
 *
 * The relocation tool moves a share's roots by deleting the old `filemeta_v0`
 * key and adding the new one in a single CRDT transaction, keeping item ids.
 * `FolderIndex.applyRemoteChange()` turns that pair into an alias, but its
 * observer is only attached after the first fresh sync, so a client that was
 * offline for the move never sees the transaction as a rename: the old local
 * folder looks like brand-new files and is published again under fresh ids.
 *
 * Comparing the persisted records (taken before the fresh sync) with the
 * synced ones restores the information the observer missed.
 */

export interface RecordSnapshotEntry {
	id: string;
	type: string;
}

export type RecordSnapshot = Map<string, RecordSnapshotEntry>;

export interface ServerMove {
	from: string;
	to: string;
}

/** Top-level folder the relocation tool moves roots into. */
export const RELOCATION_ROOT = "artifacts";

/**
 * Synced paths are untrusted input to a local rename: reject anything that
 * is absolute, uses backslashes, or has an empty, `.` or `..` segment.
 */
export function isSafeRelativePath(path: string): boolean {
	if (!path || path.startsWith("/") || path.includes("\\")) return false;
	return path.split("/").every((seg) => seg !== "" && seg !== "." && seg !== "..");
}

export function takeRecordSnapshot(source: {
	eachRecord(callback: (meta: { id: string; type: string }, path: string) => void): void;
}): RecordSnapshot {
	const snapshot: RecordSnapshot = new Map();
	source.eachRecord((meta, path) => snapshot.set(path, { id: meta.id, type: meta.type }));
	return snapshot;
}

/**
 * Moves between two snapshots, outermost only (a moved folder carries its
 * children, so their moves are implied).
 *
 * 1. Same id and type at a new path, old path gone: a plain move.
 * 2. A top-level folder gone while `artifacts/<name>` appeared as a folder
 *    (new, or already there with another id): the tool's duplicate-root
 *    merge, which keeps the destination copy's ids.
 */
export function findServerMoves(before: RecordSnapshot, after: RecordSnapshot): ServerMove[] {
	const afterById = new Map<string, string>();
	for (const [path, entry] of after) {
		if (!before.has(path)) afterById.set(`${entry.type}:${entry.id}`, path);
	}

	const moves: ServerMove[] = [];
	for (const [path, entry] of before) {
		if (after.has(path)) continue;
		const sameId = afterById.get(`${entry.type}:${entry.id}`);
		if (sameId !== undefined) {
			moves.push({ from: path, to: sameId });
			continue;
		}
		const target = `${RELOCATION_ROOT}/${path}`;
		if (
			entry.type === "folder" &&
			!path.includes("/") &&
			after.get(target)?.type === "folder"
		) {
			moves.push({ from: path, to: target });
		}
	}

	const implied = (move: ServerMove) =>
		moves.some(
			(outer) =>
				outer !== move &&
				move.from.startsWith(`${outer.from}/`) &&
				move.to === outer.to + move.from.slice(outer.from.length),
		);
	return moves.filter(
		(move) => isSafeRelativePath(move.from) && isSafeRelativePath(move.to) && !implied(move),
	);
}

/** True when `vpath` is one of the skipped roots or lies inside one. */
export function isUnderSkippedPath(vpath: string, skipped: Iterable<string>): boolean {
	for (const root of skipped) {
		if (vpath === root || vpath.startsWith(`${root}/`)) return true;
	}
	return false;
}
