import { describe, expect, jest, test } from "@jest/globals";
import type { ButtonComponent } from "obsidian";
import { setDestructiveButton } from "../src/ui/destructiveButton";

describe("destructive button compatibility", () => {
	test("uses setDestructive on Obsidian 1.13+ and preserves chaining", () => {
		const button = {
			buttonEl: { addClass: jest.fn() },
			setDestructive: jest.fn<() => ButtonComponent>(),
		};
		button.setDestructive.mockReturnValue(button as unknown as ButtonComponent);

		expect(setDestructiveButton(button as unknown as ButtonComponent)).toBe(button);
		expect(button.setDestructive).toHaveBeenCalledTimes(1);
		expect(button.buttonEl.addClass).not.toHaveBeenCalled();
	});

	test("preserves the legacy destructive style on supported Obsidian before 1.13", () => {
		const button = { buttonEl: { addClass: jest.fn() } };

		expect(setDestructiveButton(button as unknown as ButtonComponent)).toBe(button);
		expect(button.buttonEl.addClass).toHaveBeenCalledWith("mod-warning");
	});
});
