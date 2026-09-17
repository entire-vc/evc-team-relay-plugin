import { describe, expect, jest, test } from "@jest/globals";
import { Document } from "../src/Document";

describe("Document IndexedDB timeout fallback", () => {
	test("does not let blocked metadata persistence hold the relay download lane", async () => {
		const persistence = {
			synced: false,
			rememberOrigin: jest.fn(() => new Promise<never>(() => undefined)),
			loadOrigin: jest.fn(() => new Promise<never>(() => undefined)),
			rememberServerSync: jest.fn(() => new Promise<never>(() => undefined)),
			loadServerSyncFlag: jest.fn(() => new Promise<never>(() => undefined)),
			get: jest.fn(() => new Promise<never>(() => undefined)),
			set: jest.fn(() => new Promise<never>(() => undefined)),
		};
		const doc = Object.create(Document.prototype) as Document & {
			localDbTimedOut: boolean;
			_indexeddbPersistence: typeof persistence;
		};
		doc.localDbTimedOut = true;
		doc._indexeddbPersistence = persistence;

		await expect(doc.markSyncOrigin("remote")).resolves.toBeUndefined();
		await expect(doc.getSyncOrigin()).resolves.toBeUndefined();
		await expect(doc.markServerAcked()).resolves.toBeUndefined();
		await expect(doc.getServerAcked()).resolves.toBe(false);
		await expect(doc.getSyncBase()).resolves.toBeUndefined();
		await expect(doc.setSyncBase("relay contents")).resolves.toBeUndefined();

		expect(persistence.rememberOrigin).not.toHaveBeenCalled();
		expect(persistence.loadOrigin).not.toHaveBeenCalled();
		expect(persistence.rememberServerSync).not.toHaveBeenCalled();
		expect(persistence.loadServerSyncFlag).not.toHaveBeenCalled();
		expect(persistence.get).not.toHaveBeenCalled();
		expect(persistence.set).not.toHaveBeenCalled();
	});
});
