/**
 * Regression test: Mesh #0d7bcf0f — TransferQueue.pullIfUnchanged() silently
 * discarded the losing client's unsynced edit in the two-client restart race
 * (Mesh #dc11277f), with NO conflict-copy and no trace.
 *
 * Root cause (traced live with temporary instrumentation against the
 * self-hosted stand, see task comments): pullIfUnchanged()'s only guard
 * against clobbering a local edit was "the vault file didn't change DURING
 * this call's own ~2s connect+grace window". That proves the file was
 * stable while this call watched it, not that its content is actually
 * synced. An edit written straight to disk (app.vault.modify() with no live
 * editor binding) that landed BEFORE this call started, and then simply sat
 * there because the client that owns pushing it is offline/mid-restart,
 * satisfies "unchanged" trivially and used to be overwritten with the
 * relay's stale content — no conflict copy, no trace. Live-reproduced 6/6:
 * `/tmp/tr-mechb-probe.log` from the investigation instrumentation caught
 * `pullIfUnchanged CHECK unchanged=true ... WRITING remoteText over vault
 * (OVERWRITE, no conflict-copy)` clobbering a live, never-yet-synced local
 * edit on both sides of the race.
 *
 * Fix: same invariant uploadDocumentViaSocket()/reconcileRelayContent()
 * already use — check the vault content against `Document.getSyncBase()`
 * (what THIS client last CONFIRMED it and the relay agreed on), not just
 * against a same-call snapshot, before ever overwriting. A recorded,
 * diverging base means a genuine unsynced edit: preserve it as a
 * conflict-copy first. No recorded base at all means we can't tell a
 * genuine edit apart from this client's own in-flight seed/upload racing
 * the read (the exact #e1c182a2 false-positive class pullIfUnchanged was
 * built to avoid) — skip the write entirely rather than guess.
 *
 * These tests exercise the real `TransferQueue.pullIfUnchanged()` against a
 * minimal duck-typed Document (real `Document.prototype` in its chain) —
 * same pattern as syncBaseNoConflictCopy.test.ts. Timers are driven by a
 * fake Clock that fires every scheduled callback on the next macrotask, so
 * pullIfUnchanged()'s internal connect-timeout race and fixed grace delay
 * resolve immediately instead of costing real wall-clock seconds per test.
 */

import { describe, test, expect, jest } from "@jest/globals";
import type { Clock } from "../src/Clock";
import { TransferQueue } from "../src/TransferQueue";
import { Document } from "../src/Document";

/** Fires every scheduled timeout/interval callback on the next macrotask,
 * regardless of the requested delay -- keeps pullIfUnchanged()'s internal
 * raceTimeout()/delay() calls from costing real wall-clock time in tests. */
class InstantClock implements Clock {
	now(): number {
		return Date.now();
	}
	scheduleTimeout(callback: () => void): number {
		setImmediate(callback);
		return 0;
	}
	scheduleInterval(callback: () => void): number {
		setImmediate(callback);
		return 0;
	}
	cancelTimeout(): void {}
	cancelInterval(): void {}
	teardown(): void {}
	debounced<T extends (...args: unknown[]) => void>(func: T): (...args: Parameters<T>) => void {
		return (...args: Parameters<T>) => func(...args);
	}
}

interface FakeDocOptions {
	/** What's currently on disk when pullIfUnchanged() is called. */
	vaultContents: string;
	/** What the relay's Y.Doc currently holds (post fresh-sync). */
	remoteText: string;
	/** The last text this client recorded as agreeing with the relay on, or undefined if never set. */
	syncBase: string | undefined;
	/** Whether the doc's folder still tracks this path (default true). */
	tracked?: boolean;
}

function makeFakeDoc(opts: FakeDocOptions) {
	const writeConflictCopy = jest
		.fn<(doc: unknown, content: string, label: string) => Promise<string>>()
		.mockResolvedValue("note (relay conflict TIMESTAMP).md");
	const writeContents = jest.fn<(doc: unknown, content: string) => Promise<void>>().mockResolvedValue(undefined);

	const fakeDoc = Object.create(Document.prototype) as Document;
	Object.defineProperty(fakeDoc, "entryPath", { value: "note.md" });
	Object.defineProperty(fakeDoc, "entityGuid", { value: "test-guid" });
	Object.defineProperty(fakeDoc, "editLock", { value: false });
	Object.defineProperty(fakeDoc, "resourceAddress", { value: {} });
	Object.defineProperty(fakeDoc, "awaitFirstSync", { value: async () => {} });
	Object.defineProperty(fakeDoc, "content", { get: () => opts.remoteText });
	Object.defineProperty(fakeDoc, "connectionIntent", { get: () => "disconnected" });
	Object.defineProperty(fakeDoc, "bringOnline", { value: async () => true });
	Object.defineProperty(fakeDoc, "onceOnline", { value: async () => {} });
	Object.defineProperty(fakeDoc, "goOffline", { value: () => {} });
	Object.defineProperty(fakeDoc, "getSyncBase", { value: async () => opts.syncBase });
	Object.defineProperty(fakeDoc, "vaultShare", {
		value: {
			readContents: async () => opts.vaultContents,
			writeConflictCopy,
			writeContents,
			folderIndex: { tracks: () => opts.tracked ?? true },
			credentialCache: { dropFromQueue: () => {} },
		},
	});

	return { fakeDoc, writeConflictCopy, writeContents };
}

function makeQueue(): TransferQueue {
	return new TransferQueue({} as never, new InstantClock(), {} as never);
}

describe("pullIfUnchanged — sync-base gates the overwrite, never silently discards (#0d7bcf0f)", () => {
	test("REGRESSION: unsynced local edit sitting unchanged since the last agreed sync — preserved as conflict copy, not silently discarded", async () => {
		// Exactly the live-reproduced #0d7bcf0f trace: this client successfully
		// synced "initial" once (recorded as syncBase), then wrote an edit
		// straight to disk (no live editor binding) that never made it back
		// to the relay before this poll tick ran. The file hasn't moved DURING
		// this call's own window, so the old code's only guard was satisfied.
		const { fakeDoc, writeConflictCopy, writeContents } = makeFakeDoc({
			vaultContents: "B-EDIT-DURING-RESTART",
			remoteText: "TWO-CLIENT-RESTART-PROBE initial",
			syncBase: "TWO-CLIENT-RESTART-PROBE initial",
		});

		const queue = makeQueue();
		await queue.pullIfUnchanged(fakeDoc);

		expect(writeConflictCopy).toHaveBeenCalledTimes(1);
		expect(writeConflictCopy).toHaveBeenCalledWith(
			fakeDoc,
			"B-EDIT-DURING-RESTART",
			expect.stringMatching(/^relay conflict /),
		);
		// The relay's content still lands on the main file -- preserved, not blocked.
		expect(writeContents).toHaveBeenCalledWith(fakeDoc, "TWO-CLIENT-RESTART-PROBE initial");
	});

	test("no recorded sync base yet: skips the write entirely rather than guess (avoids reintroducing #e1c182a2)", async () => {
		// This doc has never completed a successful uploadDocumentViaSocket
		// cycle -- e.g. VaultShare.publishDoc()'s raw Y.Text insert is still
		// mid-seed and racing this read. We cannot tell that apart from a
		// genuine unsynced edit here, so neither overwrite NOR conflict-copy.
		const { fakeDoc, writeConflictCopy, writeContents } = makeFakeDoc({
			vaultContents: "freshly seeded content",
			remoteText: "",
			syncBase: undefined,
		});

		const queue = makeQueue();
		await queue.pullIfUnchanged(fakeDoc);

		expect(writeConflictCopy).not.toHaveBeenCalled();
		expect(writeContents).not.toHaveBeenCalled();
	});

	test("vault content matches the last confirmed sync base: safe to overwrite directly, no conflict copy needed", async () => {
		// Nothing local has changed since we last agreed with the relay --
		// this is the ordinary "peer edited a closed file" case the poller
		// exists for (#e1c182a2). The relay genuinely moved; our own content
		// did not.
		const { fakeDoc, writeConflictCopy, writeContents } = makeFakeDoc({
			vaultContents: "shared content",
			remoteText: "shared content EDITED BY PEER",
			syncBase: "shared content",
		});

		const queue = makeQueue();
		await queue.pullIfUnchanged(fakeDoc);

		expect(writeConflictCopy).not.toHaveBeenCalled();
		expect(writeContents).toHaveBeenCalledWith(fakeDoc, "shared content EDITED BY PEER");
	});

	test("relay content already matches disk: no write, no conflict copy", async () => {
		const { fakeDoc, writeConflictCopy, writeContents } = makeFakeDoc({
			vaultContents: "same everywhere",
			remoteText: "same everywhere",
			syncBase: "same everywhere",
		});

		const queue = makeQueue();
		await queue.pullIfUnchanged(fakeDoc);

		expect(writeConflictCopy).not.toHaveBeenCalled();
		expect(writeContents).not.toHaveBeenCalled();
	});
});
