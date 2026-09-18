/**
 * Tests for the vault-root path convention translation and the TFolder
 * resolver built on top of it (Mesh #2f616525 follow-up).
 *
 * `isRootSharePath`/`toSharePath` cover the wire-convention translation.
 * `resolveShareFolder` covers the actual bug this follow-up fixes: a plain
 * `vault.getAbstractFileByPath(share.path)` returns `null` for a root share
 * (Obsidian's real root `TFolder.path` is `"/"`, not the wire convention's
 * `""`), silently breaking every caller that resolves "the TFolder a share's
 * `.path` points at" without going through this helper.
 */

import { describe, test, expect } from "@jest/globals";
import { TFile, TFolder } from "./mocks/obsidian";
import {
	OBSIDIAN_VAULT_ROOT_PATH,
	isRootSharePath,
	toSharePath,
	resolveShareFolder,
	collectWebFolderItems,
	isPathWithinFolder,
} from "../src/vaultRootPath";

describe("isRootSharePath", () => {
	test("true for the empty string (wire convention for vault root)", () => {
		expect(isRootSharePath("")).toBe(true);
	});

	test("false for a real folder path", () => {
		expect(isRootSharePath("notes")).toBe(false);
	});

	test("false for Obsidian's own root path literal '/' -- that's the OTHER convention", () => {
		expect(isRootSharePath(OBSIDIAN_VAULT_ROOT_PATH)).toBe(false);
	});
});

describe("toSharePath", () => {
	test("maps Obsidian's root path '/' to the wire convention ''", () => {
		expect(toSharePath("/")).toBe("");
	});

	test("leaves a real folder path unchanged", () => {
		expect(toSharePath("notes/sub")).toBe("notes/sub");
	});
});

// Minimal duck-typed Vault -- only the two methods resolveShareFolder calls.
function fakeVault(opts: { root: TFolder; byPath?: Map<string, TFolder> }) {
	const byPath = opts.byPath ?? new Map<string, TFolder>();
	return {
		getRoot: () => opts.root,
		getAbstractFileByPath: (path: string) => byPath.get(path) ?? null,
	};
}

describe("resolveShareFolder", () => {
	test("returns vault.getRoot() for a root share path, bypassing getAbstractFileByPath", () => {
		const root = new TFolder(OBSIDIAN_VAULT_ROOT_PATH);
		const vault = fakeVault({ root });
		const resolved = resolveShareFolder(vault as any, "");
		expect(resolved).toBe(root);
	});

	test("resolves a non-root share path via getAbstractFileByPath", () => {
		const root = new TFolder(OBSIDIAN_VAULT_ROOT_PATH);
		const notes = new TFolder("notes");
		const vault = fakeVault({ root, byPath: new Map([["notes", notes]]) });
		const resolved = resolveShareFolder(vault as any, "notes");
		expect(resolved).toBe(notes);
	});

	test("returns null for a non-root path with no backing folder (deleted/renamed on disk)", () => {
		const root = new TFolder(OBSIDIAN_VAULT_ROOT_PATH);
		const vault = fakeVault({ root });
		const resolved = resolveShareFolder(vault as any, "gone");
		expect(resolved).toBeNull();
	});

	test("returns null when getAbstractFileByPath resolves to a TFile, not a TFolder", () => {
		const root = new TFolder(OBSIDIAN_VAULT_ROOT_PATH);
		// A plain object standing in for a TFile -- not `instanceof TFolder`.
		const fileStandIn = { path: "notes.md" };
		const vault = {
			getRoot: () => root,
			getAbstractFileByPath: (_path: string) => fileStandIn as any,
		};
		const resolved = resolveShareFolder(vault as any, "notes.md");
		expect(resolved).toBeNull();
	});
});

describe("collectWebFolderItems", () => {
	test("root share (folderPath '') -- top-level item path is NOT off-by-one", () => {
		// Real Obsidian: vault root TFolder.path is "/", but top-level
		// children's own `.path` has no leading slash at all ("readme.md",
		// not "/readme.md") -- this is exactly the case that a blind
		// `child.path.substring(folderPath.length + 1)` (folderPath="")
		// mishandles, chopping the first character off.
		const readme = new TFile("readme.md");
		const root = new TFolder(OBSIDIAN_VAULT_ROOT_PATH, [readme]);

		const items = collectWebFolderItems(root as any, "");

		expect(items).toEqual([{ path: "readme.md", name: "readme", type: "doc" }]);
	});

	test("root share -- nested file gets its full relative path, subfolder listed too", () => {
		const nested = new TFile("sub/note.md");
		const sub = new TFolder("sub", [nested]);
		const root = new TFolder(OBSIDIAN_VAULT_ROOT_PATH, [sub]);

		const items = collectWebFolderItems(root as any, "");

		expect(items).toEqual([
			{ path: "sub", name: "sub", type: "folder" },
			{ path: "sub/note.md", name: "note", type: "doc" },
		]);
	});

	test("non-root share -- unchanged: '<folderPath>/' prefix is stripped as before", () => {
		const child = new TFile("notes/a.md");
		const notes = new TFolder("notes", [child]);

		const items = collectWebFolderItems(notes as any, "notes");

		expect(items).toEqual([{ path: "a.md", name: "a", type: "doc" }]);
	});

	test("non-root share -- nested subfolder path is relative to the share, not the vault root", () => {
		const grandchild = new TFile("notes/sub/b.md");
		const sub = new TFolder("notes/sub", [grandchild]);
		const notes = new TFolder("notes", [sub]);

		const items = collectWebFolderItems(notes as any, "notes");

		expect(items).toEqual([
			{ path: "sub", name: "sub", type: "folder" },
			{ path: "sub/b.md", name: "b", type: "doc" },
		]);
	});

	test("canvas files are typed 'canvas', non-md/canvas files are skipped, folders always included", () => {
		const canvas = new TFile("board.canvas");
		const image = new TFile("photo.png");
		const empty = new TFolder("empty-sub");
		const root = new TFolder(OBSIDIAN_VAULT_ROOT_PATH, [canvas, image, empty]);

		const items = collectWebFolderItems(root as any, "");

		expect(items).toEqual([
			{ path: "board.canvas", name: "board", type: "canvas" },
			{ path: "empty-sub", name: "empty-sub", type: "folder" },
		]);
	});
});

describe("isPathWithinFolder", () => {
	test("root share (folderPath '') -- every real vault path is contained", () => {
		expect(isPathWithinFolder("readme.md", "")).toBe(true);
		expect(isPathWithinFolder("sub/deep/note.md", "")).toBe(true);
	});

	test("root share -- even a path that looks unrelated is still contained (root has no boundary)", () => {
		expect(isPathWithinFolder("unrelated-top-level-file.md", "")).toBe(true);
	});

	test("non-root share -- unchanged: a nested path is contained", () => {
		expect(isPathWithinFolder("notes/a.md", "notes")).toBe(true);
		expect(isPathWithinFolder("notes/sub/b.md", "notes")).toBe(true);
	});

	test("non-root share -- a sibling or unrelated path is NOT contained", () => {
		expect(isPathWithinFolder("other/a.md", "notes")).toBe(false);
		expect(isPathWithinFolder("notes-but-not-really/a.md", "notes")).toBe(false);
	});

	test("non-root share -- the folder's own path (no trailing segment) is NOT contained by this check", () => {
		// Matches the pre-existing `startsWith(folderPath + "/")` semantics this
		// helper replaces: exact-match-on-itself is the caller's job (several
		// call sites in WebSyncManager.ts explicitly OR this in separately).
		expect(isPathWithinFolder("notes", "notes")).toBe(false);
	});
});
