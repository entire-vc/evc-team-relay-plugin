import { describe, expect, jest, test } from "@jest/globals";
import { AttachmentFile } from "../src/AttachmentFile";
import { VaultShare } from "../src/VaultShare";

describe("VaultShare repairKnownLocalUploads", () => {
	test("forces known attachments back to blob storage", async () => {
		const attachment = Object.create(AttachmentFile.prototype) as AttachmentFile;
		Object.assign(attachment, {
			lastUploadError: undefined,
			pushToRemote: jest.fn(async () => {}),
		});

		const share = Object.create(VaultShare.prototype) as VaultShare;
		Object.assign(share, {
			bringOnline: jest.fn(async () => true),
			onceOnline: jest.fn(async () => {}),
			adoptLocalFiles: jest.fn(async () => {}),
			trackedEntries: new Map([["attachment", attachment]]),
			transfers: { uploadDocumentViaSocket: jest.fn() },
		});
		Object.defineProperty(share, "isOnline", { value: true, configurable: true });

		const result = await share.repairKnownLocalUploads();

		expect(share.bringOnline).toHaveBeenCalledTimes(1);
		expect(attachment.pushToRemote).toHaveBeenCalledWith(true);
		expect(result).toEqual({ total: 1, completed: 1 });
	});
});
