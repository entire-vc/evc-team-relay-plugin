import * as Y from "yjs";
import { describe, expect, jest, test } from "@jest/globals";
import { VaultShare } from "../src/VaultShare";
import { makeDocumentRecord } from "../src/ItemKinds";

describe("shared-file deletion propagation", () => {
	test("a late upload completion cannot republish metadata after deletion", async () => {
		const file = { entryPath: "deleted.md", entityGuid: "guid-1" };
		const recordUpload = jest.fn();
		const folderIndex = {
			guidFor: jest.fn(() => undefined),
			wouldChange: jest.fn(() => true),
			recordUpload,
		};
		const share = Object.create(VaultShare.prototype) as VaultShare;
		Object.assign(share, {
			folderIndex,
			trackedEntries: new Map(),
			awaitingDelete: new Set<string>(),
			crdtDoc: new Y.Doc(),
			log: jest.fn(),
			warn: jest.fn(),
		});

		(share as any)._commitMeta(file, makeDocumentRecord(file.entityGuid));

		expect(recordUpload).not.toHaveBeenCalled();
	});

	test("the current live wrapper may still commit its metadata", () => {
		const file = { entryPath: "live.md", entityGuid: "guid-2" };
		const recordUpload = jest.fn();
		const folderIndex = {
			guidFor: jest.fn(() => file.entityGuid),
			wouldChange: jest.fn(() => true),
			recordUpload,
		};
		const share = Object.create(VaultShare.prototype) as VaultShare;
		Object.assign(share, {
			folderIndex,
			trackedEntries: new Map([[file.entityGuid, file]]),
			awaitingDelete: new Set<string>(),
			crdtDoc: new Y.Doc(),
			log: jest.fn(),
			warn: jest.fn(),
		});

		const meta = makeDocumentRecord(file.entityGuid);
		(share as any)._commitMeta(file, meta);

		expect(recordUpload).toHaveBeenCalledWith(file.entryPath, meta);
	});
});
