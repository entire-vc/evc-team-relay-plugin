import { getLanguage } from "obsidian";
import { uiText } from "../src/wording/uiText";
import { resolveInterfaceLanguage } from "../src/wording/interfaceLanguage";
import { englishPhrasebook, phrasebooksByLanguage, type Phrasebook } from "../src/wording/phrasebook";

// getLanguage's ambient type (from obsidian.d.ts) is a plain `() => string` --
// the jest.fn() mock in __tests__/mocks/obsidian.ts is only a mock at
// runtime, not at the type level. Cast once, same convention as
// mockRequestUrl/mockFetch elsewhere in this test suite (platformFetch.test.ts,
// AgentKeysClient.test.ts), instead of calling .mockReturnValue() on the
// untyped import directly.
const mockGetLanguage = getLanguage as jest.MockedFunction<typeof getLanguage>;

describe("resolveInterfaceLanguage", () => {
	afterEach(() => {
		mockGetLanguage.mockReturnValue("en");
	});

	it("returns whatever Obsidian's getLanguage() reports", () => {
		mockGetLanguage.mockReturnValue("fr");
		expect(resolveInterfaceLanguage()).toBe("fr");
	});
});

describe("uiText", () => {
	afterEach(() => {
		mockGetLanguage.mockReturnValue("en");
	});

	it("returns the English phrase for the active (en) language", () => {
		mockGetLanguage.mockReturnValue("en");
		expect(uiText("shell.header.title")).toBe("Team Relay");
	});

	it("substitutes a {placeholder} from params", () => {
		expect(uiText("shareList.title", { serverName: "Acme HQ" })).toBe("Shares on Acme HQ");
	});

	it("substitutes multiple placeholders in one template", () => {
		expect(
			uiText("shareDetail.members.limitReachedNotice", { current: 5, max: 5, plan: "Free" })
		).toBe("Member limit reached (5/5 on Free plan). Upgrade your plan to add more members.");
	});

	it("leaves an unmatched {placeholder} in place rather than throwing", () => {
		expect(uiText("shareList.title")).toBe("Shares on {serverName}");
	});

	it("drops a param that has no matching placeholder, without throwing", () => {
		expect(uiText("shell.header.title", { unused: "x" })).toBe("Team Relay");
	});

	// Negative control: a language for which we ship no phrasebook at all
	// must render English, not empty strings and not the raw key.
	it("falls back to English for a language with no phrasebook (e.g. German)", () => {
		mockGetLanguage.mockReturnValue("de");
		expect(uiText("shell.header.title")).toBe(englishPhrasebook["shell.header.title"]);
		expect(uiText("shell.header.title")).not.toBe("");
		expect(uiText("shell.header.title")).not.toBe("shell.header.title");
	});

	// The fallback logic itself -- a phrasebook that exists but is MISSING a
	// specific key must fall back to English for that key, not surface
	// `undefined`/the literal key name. Uses a fake stub second-language
	// dictionary (not `ru`, which is deliberately out of scope for this MR)
	// so this proves the mechanism works before any real second language
	// ever ships.
	describe("fallback for a real phrasebook with a missing key", () => {
		const FAKE_LANG = "xx-test-stub";
		const stub: Phrasebook = {
			"shell.header.title": "Stub Title",
			// "shell.header.desc" deliberately omitted -- the gap under test.
		};

		beforeEach(() => {
			phrasebooksByLanguage[FAKE_LANG] = stub;
			mockGetLanguage.mockReturnValue(FAKE_LANG);
		});

		afterEach(() => {
			delete phrasebooksByLanguage[FAKE_LANG];
		});

		it("uses the stub phrasebook's own translation when the key exists", () => {
			expect(uiText("shell.header.title")).toBe("Stub Title");
		});

		it("falls back to English -- not undefined, not empty, not the raw key -- for a key the stub omits", () => {
			const result = uiText("shell.header.desc");
			expect(result).toBe(englishPhrasebook["shell.header.desc"]);
			expect(result).not.toBe("");
			expect(result).not.toBe("shell.header.desc");
			expect(result).not.toBeUndefined();
		});
	});
});

describe("englishPhrasebook", () => {
	it("has no empty-string values (every key resolves to real, non-blank text)", () => {
		const emptyKeys = Object.entries(englishPhrasebook)
			.filter(([, value]) => value.length === 0)
			.map(([key]) => key);
		expect(emptyKeys).toEqual([]);
	});
});
