"use strict";

import { App, PluginSettingTab } from "obsidian";
import TeamRelayPlugin from "src/main";
import SettingsPanel from "src/components/SettingsPanel.svelte";

type CloseableSetting = { setting: { close: () => void } };

export class RelaySettingsPage extends PluginSettingTab {
	// Not renamed: `PluginSettingTab`'s own base (`SettingTab`) conventionally
	// stores its constructor's `plugin` argument on `this.plugin` and its
	// default `getControlValue`/`setControlValue` read/write through it
	// (obsidian.d.ts doc comment: "Reads from `this.plugin.settings`").
	// This subclass doesn't call those, but renaming our own field would
	// decouple it from whatever Obsidian's base class continues to call
	// `this.plugin` internally, with zero compile error to catch it.
	plugin: TeamRelayPlugin;
	mountEl!: HTMLElement;
	private panel?: SettingsPanel;

	constructor(app: App, plugin: TeamRelayPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		this.mountEl = this.containerEl.parentElement as HTMLElement;
		this.mountEl.empty();
		void this.plugin.relayRegistry.refresh();

		this.panel = new SettingsPanel({
			target: this.mountEl,
			props: {
				live: this.plugin,
				onClose: () => (this as unknown as CloseableSetting).setting.close(),
			},
		});
	}

	showPath(path: string): void {
		this.panel?.$set({ initialPath: path });
	}

	hide(): void {
		try {
			this.panel?.$destroy();
		} catch (e: unknown) {
			console.warn(e);
		}
	}

	teardown(): void {
		this.hide();
		this.plugin = null as unknown as TeamRelayPlugin;
	}
}
