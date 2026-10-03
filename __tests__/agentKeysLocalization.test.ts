/** @jest-environment node */
import fs from "node:fs";
import path from "node:path";
import { compile, preprocess } from "svelte/compiler";
import type { SvelteComponent } from "svelte";
import { transpileModule, ModuleKind, ScriptTarget } from "typescript";
import { buildSync } from "esbuild";
import { getLanguage } from "obsidian";

let Component: typeof SvelteComponent;
let component: SvelteComponent;
let closeDom: () => void;

// Exercise the rendered component, including both entry points into the dialog.
// Only the host and key service boundaries are replaced.
beforeAll(async () => {
	const { JSDOM } = await import("jsdom");
	const dom = new JSDOM("<!doctype html><html><body></body></html>");
	closeDom = () => dom.window.close();
	Object.assign(globalThis, { window: dom.window, document: dom.window.document,
		activeDocument: dom.window.document, Event: dom.window.Event });
	const filename = path.resolve(__dirname, "../src/components/AgentKeysView.svelte");
	const source = await preprocess(fs.readFileSync(filename, "utf8"), {
		script: ({ content }) => ({ code: transpileModule(content, {
			compilerOptions: { module: ModuleKind.ESNext, target: ScriptTarget.ES2020, verbatimModuleSyntax: true },
		}).outputText }),
	}, { filename });
	const { js } = compile(source.code, { filename, generate: "dom" });
	const bundled = buildSync({
		stdin: { contents: js.code, resolveDir: path.dirname(filename) },
		bundle: true, write: false, format: "cjs", platform: "browser",
		external: ["obsidian", "../wording/uiText"],
	}).outputFiles[0].text;
	const loaded = { exports: {} as { default: typeof SvelteComponent } };
	const dependencies: Record<string, unknown> = {
		obsidian: { Notice: jest.fn() },
		"../wording/uiText": await import("../src/wording/uiText"),
	};
	new Function("require", "module", "exports", bundled)((id: string) => {
		if (!(id in dependencies)) throw new Error(`Unexpected dependency: ${id}`);
		return dependencies[id];
	}, loaded, loaded.exports);
	Component = loaded.exports.default;
});

async function flush() {
	await new Promise<void>((resolve) => setImmediate(resolve));
}

async function click(selector: string) {
	const button = document.querySelector<HTMLButtonElement>(selector);
	expect(button).not.toBeNull();
	button!.click();
	await flush();
}

afterAll(() => closeDom?.());
afterEach(() => {
	component?.$destroy();
	document.body.innerHTML = "";
});

describe.each([
	{ language: "en", title: "Agent Keys", headerButton: "+ Create agent key", shareButton: "+ Create key",
		empty: "No keys for this share.", dialog: "Create agent key", labels: ["Label", "Share", "Expiry"],
		placeholder: "e.g. ci-bot", expiry: ["Never", "30 days", "90 days", "1 year"],
		footer: ["Cancel", "Create key"] },
	{ language: "ru", title: "Ключи агента", headerButton: "+ Создать ключ агента", shareButton: "+ Создать ключ",
		empty: "Для этого общего доступа нет ключей.", dialog: "Создать ключ агента",
		labels: ["Название", "Общий доступ", "Срок действия"], placeholder: "например, ci-bot",
		expiry: ["Бессрочно", "30 дней", "90 дней", "1 год"], footer: ["Отмена", "Создать ключ"] },
])("agent key interface ($language)", (copy) => {
	beforeEach(async () => {
		(getLanguage as jest.Mock).mockReturnValue(copy.language);
		component = new Component({ target: document.body, props: {
			server: { id: "fixture-server" },
			live: {
				shareClient: {
					listShares: async () => [{ id: "fixture-share", path: "Folder", owner_user_id: "owner" }],
					listAgentKeys: async () => [],
				},
				authSession: { getMultiServerAuthManager: () => ({ getUserForServer: () => ({ id: "owner" }) }) },
			},
		} });
		await flush();
	});

	test("heading, both create buttons, and empty state use the selected language", () => {
		expect(document.querySelector(".ak-title")?.textContent).toBe(copy.title);
		expect(document.querySelector(".ak-header-row button")?.textContent).toBe(copy.headerButton);
		expect(document.querySelector(".ak-share-header button")?.textContent).toBe(copy.shareButton);
		expect(document.querySelector(".ak-no-keys")?.textContent).toBe(copy.empty);
	});

	test.each([".ak-header-row button", ".ak-share-header button"])("%s opens a translated dialog", async (selector) => {
		await click(selector);
		expect(document.querySelector(".ak-modal-title")?.textContent).toBe(copy.dialog);
		expect([...document.querySelectorAll(".ak-field label")].map((node) => node.textContent)).toEqual(copy.labels);
		expect(document.querySelector<HTMLInputElement>("#ak-label-input")?.placeholder).toBe(copy.placeholder);
		expect([...document.querySelectorAll("#ak-expiry-select option")].map((node) => node.textContent)).toEqual(copy.expiry);
		expect([...document.querySelectorAll(".ak-modal-footer button")].map((node) => node.textContent?.trim())).toEqual(copy.footer);
		expect(document.querySelector<HTMLSelectElement>("#ak-share-select")?.value).toBe("fixture-share");
	});
});
