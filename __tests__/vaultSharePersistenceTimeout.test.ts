import { VaultShare } from "../src/VaultShare";

describe("VaultShare IndexedDB timeout fallback", () => {
	const makeShare = (isAuthority: boolean) => {
		const share = Object.create(VaultShare.prototype) as VaultShare & {
			localDbTimedOut: boolean;
			isAuthority: boolean;
			_localDb: {
				holdsContent: jest.Mock;
				loadServerSyncFlag: jest.Mock;
			};
		};
		share.localDbTimedOut = true;
		share.isAuthority = isAuthority;
		share.awaitSynced = jest.fn(async () => undefined);
		share._localDb = {
			holdsContent: jest.fn(() => false),
			loadServerSyncFlag: jest.fn(async () => false),
		};
		return share;
	};

	it("forces a member to bootstrap from the relay without reading the blocked cache", async () => {
		const share = makeShare(false);

		await expect(share.hasPendingUpdates()).resolves.toBe(true);
		expect(share._localDb.holdsContent).not.toHaveBeenCalled();
		expect(share._localDb.loadServerSyncFlag).not.toHaveBeenCalled();
	});

	it("lets an owner continue from files already on disk", async () => {
		const share = makeShare(true);

		await expect(share.hasPendingUpdates()).resolves.toBe(false);
		expect(share._localDb.holdsContent).not.toHaveBeenCalled();
		expect(share._localDb.loadServerSyncFlag).not.toHaveBeenCalled();
	});
});
