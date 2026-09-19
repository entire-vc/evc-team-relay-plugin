import "fake-indexeddb/auto";
import * as Y from "yjs";
import { LocalDocumentStore } from "../src/storage/local-document-store";

// Regression for #be41a2ec: a freshly-opened store's own constructor read
// `this.get(KEY_SERVER_SYNC)`/`this.get(KEY_ORIGIN)` -- and `get()` awaits
// `this._dbref`, the very promise whose `.then()` callback was running that
// statement. A promise cannot settle before its own callback returns, so
// this was a deterministic deadlock, not a timing race: `synced` never
// became `true`, `emit("synced")` never fired, and every caller gated on
// `awaitSynced()` (a new folder share's whole adopt-local-files path, among
// others) hung forever. Reproduced identically on every construction --
// fresh AND reopening an existing on-disk database -- since this store
// replaced the vendored y-indexeddb implementation (867e818, 2026-09-07).
describe("LocalDocumentStore", () => {
	function withTimeout<T>(p: Promise<T>, ms: number, label: string): Promise<T> {
		return Promise.race([
			p,
			new Promise<T>((_, reject) =>
				setTimeout(() => reject(new Error(`${label}: timed out after ${ms}ms`)), ms),
			),
		]);
	}

	test("a fresh store (no prior on-disk data) reaches synced", async () => {
		const doc = new Y.Doc();
		const store = new LocalDocumentStore(`fresh-${Math.random()}`, doc);

		await withTimeout(store.whenSynced, 2000, "whenSynced");

		expect(store.synced).toBe(true);
	});

	test("reopening an existing on-disk database also reaches synced, with prior content and server-sync flag intact", async () => {
		const name = `reopen-${Math.random()}`;

		const doc1 = new Y.Doc();
		const store1 = new LocalDocumentStore(name, doc1);
		await withTimeout(store1.whenSynced, 2000, "first open");
		doc1.getText("t").insert(0, "hello");
		// The doc's own "update" event handler persists to IDB asynchronously;
		// give it a tick before asserting the second store sees it.
		await new Promise((r) => setTimeout(r, 50));
		await store1.rememberServerSync();

		const doc2 = new Y.Doc();
		const store2 = new LocalDocumentStore(name, doc2);
		await withTimeout(store2.whenSynced, 2000, "reopen");

		expect(store2.synced).toBe(true);
		expect(store2.serverSyncKnown).toBe(true);
		expect(doc2.getText("t").toString()).toBe("hello");
	});

	test("get()/set() work correctly once a store is open", async () => {
		const doc = new Y.Doc();
		const store = new LocalDocumentStore(`getset-${Math.random()}`, doc);
		await withTimeout(store.whenSynced, 2000, "whenSynced");

		expect(await store.get("missing-key")).toBeUndefined();
		await store.set("k", "v");
		expect(await store.get("k")).toBe("v");
	});
});
