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
import { TFolder } from "./mocks/obsidian";
import {
	OBSIDIAN_VAULT_ROOT_PATH,
	isRootSharePath,
	toSharePath,
	resolveShareFolder,
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
