import { describe, expect, jest, test } from "@jest/globals";
import { TFile } from "obsidian";
import { VaultShare } from "../src/VaultShare";

type ResolveLocalDoc = (
	tfile: TFile,
	newPaths: string[],
	lostPaths: Set<string>,
) => Promise<unknown>;

function makeFakeVaultShare() {
	const fake = Object.create(VaultShare.prototype);
	Object.assign(fake, {
		toVirtualPath: jest.fn((path: string) => path.replace(/^Shared\//, "")),
		entryFor: jest.fn(() => ({ kind: "existing" })),
		publishDoc: jest.fn(() => ({ kind: "published" })),
		adoptWinnerDoc: jest.fn(async () => ({ kind: "winner" })),
	});
	return fake as VaultShare & {
		entryFor: jest.Mock;
		publishDoc: jest.Mock;
		adoptWinnerDoc: jest.Mock;
	};
}

async function resolve(
	fake: VaultShare,
	newPaths: string[],
	lostPaths: Set<string> = new Set(),
) {
	const method = (fake as unknown as { _resolveLocalDoc: ResolveLocalDoc })._resolveLocalDoc;
	return method.call(fake, new TFile("Shared/note.md"), newPaths, lostPaths);
}

describe("VaultShare initial child-document publish routing", () => {
	test("a path minted in this pass bypasses entryFor and is explicitly published", async () => {
		const fake = makeFakeVaultShare();

		const result = await resolve(fake, ["note.md"]);

		expect(fake.entryFor).not.toHaveBeenCalled();
		expect(fake.publishDoc).toHaveBeenCalledWith("note.md", false);
		expect(fake.adoptWinnerDoc).not.toHaveBeenCalled();
		expect(result).toEqual({ kind: "published" });
	});

	test("a path already known before this pass still resolves through entryFor", async () => {
		const fake = makeFakeVaultShare();

		const result = await resolve(fake, []);

		expect(fake.entryFor).toHaveBeenCalledWith(expect.any(TFile), false);
		expect(fake.publishDoc).not.toHaveBeenCalled();
		expect(fake.adoptWinnerDoc).not.toHaveBeenCalled();
		expect(result).toEqual({ kind: "existing" });
	});

	test("a freshly minted path that lost the upload claim adopts the winner", async () => {
		const fake = makeFakeVaultShare();

		const result = await resolve(fake, ["note.md"], new Set(["note.md"]));

		expect(fake.entryFor).not.toHaveBeenCalled();
		expect(fake.publishDoc).not.toHaveBeenCalled();
		expect(fake.adoptWinnerDoc).toHaveBeenCalledWith("note.md");
		expect(result).toEqual({ kind: "winner" });
	});
});
