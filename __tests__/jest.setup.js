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
// Instance-method versions of the same helpers (`el.createEl(...)`, not the
// free function above) — real Obsidian patches these onto Node.prototype so
// any Element/DocumentFragment can build+append children fluently (used e.g.
// by createFragment(el => el.createSpan(...)) callbacks). Guarded on `Node`
// existing: in a plain node-env test file (no jsdom) `Node` itself isn't
// defined, so this block is a no-op there, same as the free-function
// polyfills above being no-ops without `document`.
if (typeof Node !== "undefined" && typeof Node.prototype.createEl === "undefined") {
	Node.prototype.createEl = function (tag, o, callback) {
		const el = applyDomElementInfo(document.createElement(tag), o);
		this.appendChild(el);
		if (callback) callback(el);
		return el;
	};
	Node.prototype.createDiv = function (o, callback) {
		return this.createEl("div", o, callback);
	};
	Node.prototype.createSpan = function (o, callback) {
		return this.createEl("span", o, callback);
	};
}
if (typeof global.createFragment === "undefined" && typeof document !== "undefined") {
	global.createFragment = (callback) => {
		const fragment = document.createDocumentFragment();
		if (callback) callback(fragment);
		return fragment;
	};
}
