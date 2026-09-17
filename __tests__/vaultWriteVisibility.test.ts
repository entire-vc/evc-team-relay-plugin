import { describe, expect, jest, test } from "@jest/globals";
import { TFile, TFolder } from "obsidian";
import { VaultShare } from "../src/VaultShare";

function makeShare(vaultOverrides: Record<string, unknown> = {}) {
	const adapter = {
		exists: jest.fn(async () => false),
		write: jest.fn(async () => {}),
	};
	const vaultApi = {
		adapter,
		getAbstractFileByPath: jest.fn(() => null),
		create: jest.fn(async (path: string) => new TFile(path)),
		modify: jest.fn(async () => {}),
		createFolder: jest.fn(async (path: string) => new TFolder(path)),
		...vaultOverrides,
	};
	const share = Object.create(VaultShare.prototype) as VaultShare;
	Object.assign(share, {
		path: "Shared",
		vaultApi,
		isDeletePending: jest.fn(() => false),
		log: jest.fn(),
	});
	return { share, vaultApi, adapter };
}

describe("VaultShare inbound writes are visible to Obsidian", () => {
	test("does not try to create the dot sentinel for a root-level relay entry", async () => {
		const { share, vaultApi } = makeShare();

		await (share as unknown as {
			_ensureParentDir: (path: string) => Promise<void>;
		})._ensureParentDir("Peer note.md");

		expect(vaultApi.createFolder).not.toHaveBeenCalled();
	});

	test("creates a new relay document through Vault.create", async () => {
		const { share, vaultApi, adapter } = makeShare();

		await share.writeContents({ entryPath: "Peer note.md" } as never, "from relay");

		expect(vaultApi.create).toHaveBeenCalledWith("Shared/Peer note.md", "from relay");
		expect(adapter.write).not.toHaveBeenCalled();
	});

	test("modifies an indexed relay document through Vault.modify", async () => {
		const file = new TFile("Shared/Peer note.md");
		const { share, vaultApi } = makeShare({
			getAbstractFileByPath: jest.fn(() => file),
		});

		await share.writeContents({ entryPath: "Peer note.md" } as never, "updated");

		expect(vaultApi.modify).toHaveBeenCalledWith(file, "updated");
		expect(vaultApi.create).not.toHaveBeenCalled();
	});

	test("creates a downloaded folder through Vault.createFolder", async () => {
		const { share, vaultApi } = makeShare();

		await share.makeFolder("From peer");

		expect(vaultApi.createFolder).toHaveBeenCalledWith("Shared/From peer");
	});
});
