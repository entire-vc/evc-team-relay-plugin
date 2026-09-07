import { getLanguage } from "obsidian";
import { uiText } from "../src/wording/uiText";
import { resolveInterfaceLanguage } from "../src/wording/interfaceLanguage";
import {
	englishPhrasebook,
	ruPhrasebook,
	phrasebooksByLanguage,
	type PhraseKey,
	type Phrasebook,
} from "../src/wording/phrasebook";

const PLACEHOLDER_RE = /\{([a-zA-Z0-9_]+)\}/g;
function placeholderNames(template: string): string[] {
	return [...template.matchAll(PLACEHOLDER_RE)].map((m) => m[1]).sort();
}

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
		expect(uiText("shareList.title", { serverName: "Acme HQ" })).toBe(
			"Shares on Acme HQ",
		);
	});

	it("substitutes multiple placeholders in one template", () => {
		expect(
			uiText("shareDetail.members.limitReachedNotice", {
				current: 5,
				max: 5,
				plan: "Free",
			}),
		).toBe(
			"Member limit reached (5/5 on Free plan). Upgrade your plan to add more members.",
		);
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
		expect(uiText("shell.header.title")).toBe(
			englishPhrasebook["shell.header.title"],
		);
		expect(uiText("shell.header.title")).not.toBe("");
		expect(uiText("shell.header.title")).not.toBe("shell.header.title");
	});

	// The fallback logic itself -- a phrasebook that exists but is MISSING a
	// specific key must fall back to English for that key, not surface
	// `undefined`/the literal key name. Uses a fake stub dictionary (not
	// `ru`, which is complete -- see the "ruPhrasebook" describe block below
	// for real-language coverage) so this proves the mechanism works
	// independent of any one real phrasebook's completeness.
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

describe("connect.login cross-server strings (#a1fef59b)", () => {
	afterEach(() => {
		mockGetLanguage.mockReturnValue("en");
	});

	it("connect.login.title substitutes the server name", () => {
		expect(uiText("connect.login.title", { server: "Team Relay RU" })).toBe("Sign in to Team Relay RU");
	});

	it("connect.login.titleFallback carries the old generic text, for when no server name resolves", () => {
		expect(uiText("connect.login.titleFallback")).toBe("Relay on-premise login");
	});

	it("connect.login.separateAccountsNote substitutes both server names", () => {
		expect(
			uiText("connect.login.separateAccountsNote", {
				otherServer: "EVC Team Relay",
				thisServer: "Team Relay RU",
			})
		).toBe(
			"Accounts aren't shared between servers. A login from EVC Team Relay won't work here — you need an invite to Team Relay RU."
		);
	});

	it("connect.login.incorrectCredentialsCrossServer substitutes the other server's name", () => {
		expect(uiText("connect.login.incorrectCredentialsCrossServer", { otherServer: "Team Relay RU" })).toBe(
			"Incorrect email or password. Accounts aren't shared between servers — if that login is from Team Relay RU, it won't work here."
		);
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

// #bac8b7dd MR2 -- ru phrasebook. Structural checks only: this suite proves
// the mechanism serves ru correctly and that ru's coverage/placeholders
// stay in lockstep with en as either evolves. It does NOT and cannot judge
// translation quality -- that's the human review this MR is gated on
// (CLAUDE-workflow.md §1r.A), not something a test asserts.
describe("ruPhrasebook", () => {
	it("has no empty-string values", () => {
		const emptyKeys = Object.entries(ruPhrasebook)
			.filter(([, value]) => value.length === 0)
			.map(([key]) => key);
		expect(emptyKeys).toEqual([]);
	});

	it("covers every key englishPhrasebook defines -- no silent gaps in Phase 1", () => {
		const enKeys = Object.keys(englishPhrasebook) as PhraseKey[];
		const missing = enKeys.filter((k) => !(k in ruPhrasebook));
		expect(missing).toEqual([]);
	});

	it("defines no key englishPhrasebook doesn't have -- no stray/renamed keys", () => {
		const enKeys = new Set(Object.keys(englishPhrasebook));
		const extra = Object.keys(ruPhrasebook).filter((k) => !enKeys.has(k));
		expect(extra).toEqual([]);
	});

	it("preserves the exact same {placeholder} set as English, for every key", () => {
		const mismatches: Array<{ key: string; en: string[]; ru: string[] }> = [];
		for (const key of Object.keys(englishPhrasebook) as PhraseKey[]) {
			const enPlaceholders = placeholderNames(englishPhrasebook[key]);
			const ruValue = ruPhrasebook[key];
			const ruPlaceholders = ruValue ? placeholderNames(ruValue) : [];
			if (JSON.stringify(enPlaceholders) !== JSON.stringify(ruPlaceholders)) {
				mismatches.push({ key, en: enPlaceholders, ru: ruPlaceholders });
			}
		}
		expect(mismatches).toEqual([]);
	});

	it("is registered under the 'ru' ISO code in phrasebooksByLanguage", () => {
		expect(phrasebooksByLanguage["ru"]).toBe(ruPhrasebook);
	});
});

describe("uiText with the real ru phrasebook (not a stub)", () => {
	afterEach(() => {
		mockGetLanguage.mockReturnValue("en");
	});

	it("returns the Russian phrase when Obsidian reports ru", () => {
		mockGetLanguage.mockReturnValue("ru");
		expect(uiText("shell.header.title")).toBe("Team Relay");
		expect(uiText("shareDetail.members.heading")).toBe("Участники");
	});

	it("substitutes a {placeholder} in a Russian template", () => {
		mockGetLanguage.mockReturnValue("ru");
		expect(uiText("shareList.title", { serverName: "Acme HQ" })).toBe(
			"Общие доступы на Acme HQ",
		);
	});

	it("substitutes multiple placeholders in a Russian template", () => {
		mockGetLanguage.mockReturnValue("ru");
		expect(
			uiText("shareDetail.members.limitReachedNotice", {
				current: 5,
				max: 5,
				plan: "Free",
			}),
		).toBe(
			"Достигнут лимит участников (5/5 на тарифе Free). Обновите тариф, чтобы добавить больше участников.",
		);
	});
});
