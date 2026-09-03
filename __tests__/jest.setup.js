// Polyfill browser globals for Jest Node.js test environment.
// Obsidian plugins use window.setTimeout/setInterval/etc. for popout-window
// compatibility. In Node.js test env, window is undefined — alias it to global
// so window.setTimeout === global.setTimeout (which Node.js provides natively).
if (typeof global.window === "undefined") {
	global.window = global;
}
// Node's plain global object is not an EventTarget — unlike a real
// window/activeWindow, it has no addEventListener/removeEventListener. Code
// that calls window.addEventListener/activeWindow.addEventListener (e.g. an
// "unload" cleanup listener) throws in this test env otherwise. No-op stubs
// are enough here: nothing in this test suite depends on these listeners
// actually firing, only on constructing/tearing down without throwing.
if (typeof global.addEventListener !== "function") {
	global.addEventListener = () => {};
}
if (typeof global.removeEventListener !== "function") {
	global.removeEventListener = () => {};
}
// activeWindow and activeDocument are Obsidian globals (declared in obsidian.d.ts).
// Point them at the global object so code that references them doesn't throw.
if (typeof global.activeWindow === "undefined") {
	global.activeWindow = global;
}
if (typeof global.activeDocument === "undefined") {
	global.activeDocument = global.document || {};
}
// createEl/createDiv/createSpan are also Obsidian globals (declared
// `declare global` in obsidian.d.ts, not exports of the "obsidian" module —
// same category as activeDocument/activeWindow above). Real Obsidian
// implements them as detached-element factories: build a plain element via
// document.createElement, then apply the subset of DomElementInfo this repo
// actually uses (cls/text/attr/title). Only meaningful in a jsdom-environment
// test file (`@jest-environment jsdom` docblock) where a real `document`
// exists — in a plain node-env file nothing calls these, same as
// activeDocument.createElement never being called there either.
function applyDomElementInfo(el, o) {
	const info = typeof o === "string" ? { text: o } : o || {};
	if (info.cls !== undefined) {
		const classes = Array.isArray(info.cls) ? info.cls : [info.cls];
		el.classList.add(...classes.filter((c) => typeof c === "string" && c.length > 0));
	}
	if (info.text !== undefined) {
		el.textContent = info.text;
	}
	if (info.title !== undefined) {
		el.title = info.title;
	}
	if (info.attr) {
		for (const [key, value] of Object.entries(info.attr)) {
			if (value === null || value === false) continue;
			el.setAttribute(key, value === true ? "" : String(value));
		}
	}
	return el;
}
if (typeof global.createEl === "undefined") {
	global.createEl = (tag, o) => applyDomElementInfo(global.document.createElement(tag), o);
}
if (typeof global.createDiv === "undefined") {
	global.createDiv = (o) => global.createEl("div", o);
}
if (typeof global.createSpan === "undefined") {
	global.createSpan = (o) => global.createEl("span", o);
}
