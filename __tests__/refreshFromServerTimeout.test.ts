import { afterEach, beforeEach, describe, expect, jest, test } from "@jest/globals";
import { VaultShare } from "../src/VaultShare";

function makeFakeVaultShare(overrides: Record<string, unknown> = {}) {
	const fake = Object.create(VaultShare.prototype);
	Object.assign(fake, {
		path: "test-folder",
		awaitReady: jest.fn(async () => {}),
		onceFreshlySynced: jest.fn(async () => {}),
		adoptLocalFiles: jest.fn(async () => {}),
		scanFileTree: jest.fn(async () => {}),
		folderIndex: {},
		transfers: { enqueueShareUpload: jest.fn() },
		...overrides,
	});
	return fake as VaultShare & {
		adoptLocalFiles: jest.Mock;
		scanFileTree: jest.Mock;
		transfers: { enqueueShareUpload: jest.Mock };
	};
}

describe("VaultShare.refreshFromServer() fresh-sync timeout", () => {
	beforeEach(() => {
		jest.useFakeTimers();
	});

	afterEach(() => {
		jest.useRealTimers();
		jest.restoreAllMocks();
	});

	test("a confirmed fresh sync allows normal local-file adoption", async () => {
		const fake = makeFakeVaultShare();

		await fake.refreshFromServer();

		expect(fake.adoptLocalFiles).toHaveBeenCalledWith(true);
		expect(fake.scanFileTree).toHaveBeenCalledWith(fake.folderIndex);
		expect(fake.transfers.enqueueShareUpload).toHaveBeenCalledWith(fake);
	});

	test("a missing fresh-sync event retries known pending uploads instead of hanging", async () => {
		jest.spyOn(console, "warn").mockImplementation(() => {});
		const fake = makeFakeVaultShare({
			onceFreshlySynced: jest.fn(() => new Promise<void>(() => {})),
		});

		const refresh = fake.refreshFromServer();
		await jest.advanceTimersByTimeAsync(10000);
		await refresh;

		expect(fake.adoptLocalFiles).toHaveBeenCalledWith(false);
		expect(fake.scanFileTree).toHaveBeenCalledWith(fake.folderIndex);
		expect(fake.transfers.enqueueShareUpload).toHaveBeenCalledWith(fake);
	});
});
