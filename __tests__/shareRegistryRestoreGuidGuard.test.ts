/**
 * Unit test: ShareRegistry._restoreFrom() refuses a persisted sharedFolders
 * entry with a missing/invalid guid (Mesh #0c38f743).
 *
 * The bug: a corrupt/missing `guid` field on a persisted entry (data.json
 * hand-edited, a field renamed by a bug elsewhere, a truncated write) used
 * to be passed straight through to _instantiateVaultShare(), whose
 * SettingsScope path is built as `sharedFolders/[guid=${guid}]`. A JS
 * `undefined` guid template-coerces to the literal STRING "undefined", and
 * SettingsScope's array-item writer matches existing entries by
 * `entry.guid === matchValue` -- a real `undefined` field never equals the
 * string "undefined", so it can never find the already-corrupt entry and
 * instead CREATES a brand-new one with `guid: "undefined"`. Reproduced live
 * (Verity, negative control for #9aff0bf8): one corrupt entry -> three
 * competing local records after a single restart.
 *
 * This test exercises the real ShareRegistry.restore() with a minimal fake
 * Vault/shareFactory/persistedShares -- not a reimplementation of the guard,
 * so it actually proves the integration, not just the condition in isolation.
 */

import { describe, test, expect, jest } from "@jest/globals";
import { ShareRegistry, type VaultShareSettings } from "../src/VaultShare";

function makeVault(existingPaths: string[]) {
	return {
		getFolderByPath: (path: string) => (existingPaths.includes(path) ? { path } : null),
	};
}

describe("ShareRegistry.restore() -- guid guard (#0c38f743)", () => {
	test("an entry with guid: undefined is refused, not passed to the factory", () => {
		const shareFactory = jest.fn(
			(path: string, guid: string, workspaceId?: string, hasPendingUpdates?: boolean, isRestore?: boolean) =>
				({ path, entityGuid: guid }) as never,
		);
		const persistedShares = {
			readValue: (): VaultShareSettings[] => [
				{ path: "corrupt-folder", guid: undefined as unknown as string, relay: "fmt-test" },
			],
		};

		const registry = new ShareRegistry(
			{} as never,
			makeVault(["corrupt-folder"]) as never,
			shareFactory,
			persistedShares as never,
		);
		registry.restore();

		expect(shareFactory).not.toHaveBeenCalled();
	});

	test("an entry with an empty-string guid is also refused", () => {
		const shareFactory = jest.fn(
			(path: string, guid: string, workspaceId?: string, hasPendingUpdates?: boolean, isRestore?: boolean) =>
				({ path, entityGuid: guid }) as never,
		);
		const persistedShares = {
			readValue: (): VaultShareSettings[] => [{ path: "empty-guid-folder", guid: "" }],
		};

		const registry = new ShareRegistry(
			{} as never,
			makeVault(["empty-guid-folder"]) as never,
			shareFactory,
			persistedShares as never,
		);
		registry.restore();

		expect(shareFactory).not.toHaveBeenCalled();
	});

	test("a genuinely renamed field (guidBROKEN instead of guid) is refused -- the exact live repro shape", () => {
		const shareFactory = jest.fn(
			(path: string, guid: string, workspaceId?: string, hasPendingUpdates?: boolean, isRestore?: boolean) =>
				({ path, entityGuid: guid }) as never,
		);
		// Mirrors Verity's live repro exactly: the real guid moved to a
		// differently-named field, so `.guid` reads as `undefined`.
		const corrupted = {
			path: "fmt-test-folder",
			relay: "fmt-test",
			guidBROKEN: "0eab9783-d0b2-431e-abd1-f59ceeef5419",
		} as unknown as VaultShareSettings;
		const persistedShares = {
			readValue: (): VaultShareSettings[] => [corrupted],
		};

		const registry = new ShareRegistry(
			{} as never,
			makeVault(["fmt-test-folder"]) as never,
			shareFactory,
			persistedShares as never,
		);
		registry.restore();

		expect(shareFactory).not.toHaveBeenCalled();
	});

	test("a normal, valid entry alongside a corrupt one still restores cleanly -- the guard doesn't over-block", () => {
		const shareFactory = jest.fn(
			(path: string, guid: string, workspaceId?: string, hasPendingUpdates?: boolean, isRestore?: boolean) =>
				({ path, entityGuid: guid }) as never,
		);
		const persistedShares = {
			readValue: (): VaultShareSettings[] => [
				{ path: "corrupt-folder", guid: undefined as unknown as string },
				{ path: "good-folder", guid: "11111111-1111-4111-8111-111111111111", relay: "fmt-test" },
			],
		};

		const registry = new ShareRegistry(
			{} as never,
			makeVault(["corrupt-folder", "good-folder"]) as never,
			shareFactory,
			persistedShares as never,
		);
		registry.restore();

		expect(shareFactory).toHaveBeenCalledTimes(1);
		expect(shareFactory).toHaveBeenCalledWith(
			"good-folder",
			"11111111-1111-4111-8111-111111111111",
			"fmt-test",
			undefined,
			true,
		);
	});

	test("no persisted entries at all is a silent no-op (not itself a regression target, just a sanity floor)", () => {
		const shareFactory = jest.fn();
		const persistedShares = { readValue: (): VaultShareSettings[] => [] };

		const registry = new ShareRegistry(
			{} as never,
			makeVault([]) as never,
			shareFactory as never,
			persistedShares as never,
		);
		registry.restore();

		expect(shareFactory).not.toHaveBeenCalled();
	});
});
