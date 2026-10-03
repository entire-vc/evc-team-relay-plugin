import type { ButtonComponent } from "obsidian";

/** Use the current button API while keeping Obsidian 1.8.7–1.12 compatible. */
export function setDestructiveButton(button: ButtonComponent): ButtonComponent {
	if (typeof button.setDestructive === "function") {
		return button.setDestructive();
	}
	// Equivalent to the legacy button API, without calling its deprecated method.
	button.buttonEl.addClass("mod-warning");
	return button;
}
