/**
 * Offline client + server-side relocation (relocate-artifacts): the client
 * must follow the move locally instead of publishing the old root again.
 */
import { describe, test, expect, jest } from "@jest/globals";
import * as Y from "yjs";
import { VaultShare } from "../src/VaultShare";
import { FolderIndex } from "../src/FolderIndex";
import { makeFolderRecord, makeDocumentRecord } from "../src/ItemKinds";
import type { AttachmentSyncSettings } from "../src/AttachmentSyncSettings";
import {
	findServerMoves,
	isUnderSkippedPath,
	takeRecordSnapshot,
	type RecordSnapshot,
} from "../src/serverRelocation";

const snap = (entries: Record<string, [string, string]>): RecordSnapshot =>
	new Map(Object.entries(entries).map(([p, [type, id]]) => [p, { type, id }]));

describe("findServerMoves", () => {
	test("ignores moves whose paths escape the share", () => {
		const before = snap({ "aaaa1111": ["folder", "f1"], "bbbb2222": ["folder", "f2"] });
		const after = snap({
			"../Outside": ["folder", "f1"],
			"/abs": ["folder", "f2"],
		});
		expect(findServerMoves(before, after)).toEqual([]);
	});

	test("same ids at a new path are a move; children are implied by the root", () => {
		const before = snap({
			"aaaa1111": ["folder", "f1"],
			"aaaa1111/note.md": ["document", "d1"],
		});
		const after = snap({
			"artifacts/aaaa1111": ["folder", "f1"],
			"artifacts/aaaa1111/note.md": ["document", "d1"],
		});
		expect(findServerMoves(before, after)).toEqual([
			{ from: "aaaa1111", to: "artifacts/aaaa1111" },
		]);
	});

	test("duplicate-root merge: destination keeps its own ids", () => {
		const before = snap({ "aaaa1111": ["folder", "f1"] });
		const after = snap({ "artifacts/aaaa1111": ["folder", "f2"] });
		expect(findServerMoves(before, after)).toEqual([
			{ from: "aaaa1111", to: "artifacts/aaaa1111" },
		]);
	});

	test("duplicate-root merge into a destination that already existed", () => {
		const before = snap({
			"aaaa1111": ["folder", "f1"],
			"artifacts/aaaa1111": ["folder", "f2"],
		});
		const after = snap({ "artifacts/aaaa1111": ["folder", "f2"] });
		expect(findServerMoves(before, after)).toEqual([
			{ from: "aaaa1111", to: "artifacts/aaaa1111" },
		]);
	});

	test("a plain remote delete is not a move", () => {
		expect(findServerMoves(snap({ gone: ["folder", "f1"] }), snap({}))).toEqual([]);
	});

	test("untouched paths are not moves", () => {
		const same = snap({ keep: ["folder", "f1"] });
		expect(findServerMoves(same, same)).toEqual([]);
	});
});

function offlineMoveFixture() {
	const persisted = new Y.Doc();
	persisted.getMap("filemeta_v0").set("aaaa1111", makeFolderRecord("f1"));
	persisted.getMap("filemeta_v0").set("aaaa1111/note.md", makeDocumentRecord("d1"));
	persisted.getMap("docs").set("aaaa1111/note.md", "d1");

	const server = new Y.Doc();
	Y.applyUpdate(server, Y.encodeStateAsUpdate(persisted));
	server.transact(() => {
		const meta = server.getMap("filemeta_v0");
		const docs = server.getMap("docs");
		meta.delete("aaaa1111");
		meta.delete("aaaa1111/note.md");
		docs.delete("aaaa1111/note.md");
		meta.set("artifacts", makeFolderRecord("fa"));
		meta.set("artifacts/aaaa1111", makeFolderRecord("f1"));
		meta.set("artifacts/aaaa1111/note.md", makeDocumentRecord("d1"));
		docs.set("artifacts/aaaa1111/note.md", "d1");
	});

	const cache = new Y.Doc();
	Y.applyUpdate(cache, Y.encodeStateAsUpdate(persisted));
	const index = new FolderIndex(cache, "Shared", new Map(), {
		subscribe: () => () => {},
	} as unknown as AttachmentSyncSettings);

	let confirm!: () => void;
	const synced = new Promise<void>((resolve) => { confirm = resolve; });
	const local = new Set(["Shared/aaaa1111", "Shared/aaaa1111/note.md"]);
	const renames: Array<[string, string]> = [];
	const adopted: string[][] = [];

	const share = Object.create(VaultShare.prototype) as VaultShare;
	Object.assign(share, {
		path: "Shared", crdtDoc: cache, folderIndex: index,
		_wantsConnection: true, freshlyCreated: false, isTornDown: false,
		awaitSynced: async () => {}, onceFreshlySynced: () => synced,
		followedMoveSkips: new Set<string>(),
		adoptLocalFiles: jest.fn(async () => { adopted.push([...local]); }),
		scanFileTree: jest.fn(async () => {}),
		vaultApi: {
			getAbstractFileByPath: (p: string) => (local.has(p) ? { path: p } : null),
		},
		fileOps: {
			renameFile: async (file: { path: string }, to: string) => {
				renames.push([file.path, to]);
				for (const p of [...local]) {
					if (p === file.path || p.startsWith(file.path + "/")) {
						local.delete(p);
						local.add(to + p.slice(file.path.length));
					}
				}
			},
		},
		_ensureParentDir: async () => { local.add("Shared/artifacts"); },
	});
	return { cache, server, share, confirm, renames, adopted, local };
}

describe("offline client + server relocation", () => {
	test("the old root is renamed before local files are adopted", async () => {
		const f = offlineMoveFixture();
		// As in the constructor: _onSynced() starts the folder-tree barrier (and the
		// persisted snapshot) as soon as IndexedDB has loaded, before the provider syncs.
		(f.share as unknown as { _onSynced(): void })._onSynced();
		const ready = (f.share as unknown as { _onReady(): Promise<void> })._onReady();
		await new Promise((resolve) => window.setTimeout(resolve, 5));
		Y.applyUpdate(f.cache, Y.encodeStateAsUpdate(f.server));
		f.confirm();
		await ready;

		expect(f.renames).toEqual([["Shared/aaaa1111", "Shared/artifacts/aaaa1111"]]);
		expect(f.adopted).toHaveLength(1);
		expect(f.adopted[0]).toContain("Shared/artifacts/aaaa1111/note.md");
		expect(f.adopted[0]).not.toContain("Shared/aaaa1111");
		expect(takeRecordSnapshot((f.share as unknown as { folderIndex: FolderIndex }).folderIndex).has("aaaa1111")).toBe(false);
	});

	test("never overwrites a destination that already exists locally", async () => {
		const f = offlineMoveFixture();
		f.local.add("Shared/artifacts/aaaa1111");
		// As in the constructor: _onSynced() starts the folder-tree barrier (and the
		// persisted snapshot) as soon as IndexedDB has loaded, before the provider syncs.
		(f.share as unknown as { _onSynced(): void })._onSynced();
		const ready = (f.share as unknown as { _onReady(): Promise<void> })._onReady();
		await new Promise((resolve) => window.setTimeout(resolve, 5));
		Y.applyUpdate(f.cache, Y.encodeStateAsUpdate(f.server));
		f.confirm();
		await ready;
		expect(f.renames).toEqual([]);
		// The old root stays on disk but is excluded from adoption.
		expect([...(f.share as unknown as { followedMoveSkips: Set<string> }).followedMoveSkips]).toEqual(["aaaa1111"]);
	});

	test("a failed local rename keeps the old root out of adoption", async () => {
		const f = offlineMoveFixture();
		(f.share as unknown as { fileOps: { renameFile: () => Promise<void> } }).fileOps.renameFile = async () => {
			throw new Error("rename failed");
		};
		(f.share as unknown as { _onSynced(): void })._onSynced();
		const ready = (f.share as unknown as { _onReady(): Promise<void> })._onReady();
		await new Promise((resolve) => window.setTimeout(resolve, 5));
		Y.applyUpdate(f.cache, Y.encodeStateAsUpdate(f.server));
		f.confirm();
		await ready;
		expect([...(f.share as unknown as { followedMoveSkips: Set<string> }).followedMoveSkips]).toEqual(["aaaa1111"]);
	});

	test("skipped roots cover their children but not look-alike siblings", () => {
		const skips = new Set(["aaaa1111"]);
		expect(isUnderSkippedPath("aaaa1111", skips)).toBe(true);
		expect(isUnderSkippedPath("aaaa1111/note.md", skips)).toBe(true);
		expect(isUnderSkippedPath("aaaa11112/note.md", skips)).toBe(false);
		expect(isUnderSkippedPath("artifacts/aaaa1111/note.md", skips)).toBe(false);
	});
});
