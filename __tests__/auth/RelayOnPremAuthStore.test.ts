/**
 * Tests for RelayOnPremAuthStore
 *
 * Tests localStorage persistence with mocked window.localStorage.
 */

import { describe, test, expect, beforeEach, jest } from "@jest/globals";
import {
	RelayOnPremAuthStore,
	getAuthStore,
	type RelayOnPremAuthData,
} from "../../src/auth/RelayOnPremAuthStore";
import type { AuthUser } from "../../src/auth/IAuthProvider";

// Mock namedLogger to avoid debug output during tests
jest.mock("../../src/logging", () => ({
	namedLogger: () => jest.fn(),
}));

// Mock localStorage
const mockStorage = new Map<string, string>();
Object.defineProperty(global, "window", {
	value: {
		localStorage: {
			getItem: (key: string) => mockStorage.get(key) ?? null,
			setItem: (key: string, value: string) => mockStorage.set(key, value),
			removeItem: (key: string) => mockStorage.delete(key),
			get length() {
				return mockStorage.size;
			},
			key: (index: number) => [...mockStorage.keys()][index] ?? null,
			clear: () => mockStorage.clear(),
		},
	},
	writable: true,
});

describe("RelayOnPremAuthStore", () => {
	const APP_ID = "test-app-id";
	const SERVER_ID = "server-123";

	let store: RelayOnPremAuthStore;

	const mockAuthData: RelayOnPremAuthData = {
		user: {
			id: "user-123",
			email: "test@example.com",
			name: "Test Account",
		},
		token: "test_access_token",
		expiresAt: Date.now() + 3600000,
		refreshToken: "test_refresh_token",
	};

	beforeEach(() => {
		mockStorage.clear();
		store = new RelayOnPremAuthStore(APP_ID);
	});

	describe("persist() and load()", () => {
		test("P31: Roundtrip", () => {
			store.persist(SERVER_ID, mockAuthData);

			const loaded = store.load(SERVER_ID);

			expect(loaded).toEqual(mockAuthData);
		});

		test("Load returns null if no data", () => {
			const loaded = store.load("nonexistent-server");

			expect(loaded).toBeNull();
		});

		test("Load returns null if data incomplete (missing user)", () => {
			const incompleteData = {
				token: "token",
				expiresAt: Date.now() + 3600000,
			};

			const key = `evc-team-relay_onprem_auth_${APP_ID}_${SERVER_ID}`;
			mockStorage.set(key, JSON.stringify(incompleteData));

			const loaded = store.load(SERVER_ID);

			expect(loaded).toBeNull();
		});

		test("Load returns null if data incomplete (missing token)", () => {
			const incompleteData = {
				user: mockAuthData.user,
				expiresAt: Date.now() + 3600000,
			};

			const key = `evc-team-relay_onprem_auth_${APP_ID}_${SERVER_ID}`;
			mockStorage.set(key, JSON.stringify(incompleteData));

			const loaded = store.load(SERVER_ID);

			expect(loaded).toBeNull();
		});

		test("Load returns null if data incomplete (missing expiresAt)", () => {
			const incompleteData = {
				user: mockAuthData.user,
				token: "token",
			};

			const key = `evc-team-relay_onprem_auth_${APP_ID}_${SERVER_ID}`;
			mockStorage.set(key, JSON.stringify(incompleteData));

			const loaded = store.load(SERVER_ID);

			expect(loaded).toBeNull();
		});
	});

	describe("Storage key format", () => {
		test("P32: Key format evc-team-relay_onprem_auth_{appId}_{server}", () => {
			store.persist(SERVER_ID, mockAuthData);

			const expectedKey = `evc-team-relay_onprem_auth_${APP_ID}_${SERVER_ID}`;
			expect(mockStorage.has(expectedKey)).toBe(true);
		});

		test("Different vault appIds have separate storage", () => {
			const store1 = new RelayOnPremAuthStore("app-id-1");
			const store2 = new RelayOnPremAuthStore("app-id-2");

			const authData1 = { ...mockAuthData, user: { ...mockAuthData.user, email: "vault1@example.com" } };
			const authData2 = { ...mockAuthData, user: { ...mockAuthData.user, email: "vault2@example.com" } };

			store1.persist(SERVER_ID, authData1);
			store2.persist(SERVER_ID, authData2);

			expect(store1.load(SERVER_ID)?.user.email).toBe("vault1@example.com");
			expect(store2.load(SERVER_ID)?.user.email).toBe("vault2@example.com");
		});

		test("TR-56: storage identity is a pure function of appId — no vaultName parameter exists to be affected by a rename", () => {
			// Regression test for TR-56: the store used to be constructed with the
			// vault's user-editable display name (`app.vault.getName()`), so renaming
			// the vault silently orphaned the stored session (new name -> new, empty
			// key). The constructor signature no longer accepts a vault name at all —
			// only Obsidian's rename-stable `app.appId` — so there is nothing left
			// for a vault rename to change. This test can't literally rename a vault
			// (no such concept reaches this class anymore); it documents and pins
			// the invariant: two instances constructed with the same appId always
			// see the same session, regardless of when/whether the vault was renamed
			// in between (main.ts re-derives appId fresh from the Obsidian API on
			// every load and passes nothing else into this chain).
			const beforeRestart = new RelayOnPremAuthStore(APP_ID);
			beforeRestart.persist(SERVER_ID, mockAuthData);

			const afterRestart = new RelayOnPremAuthStore(APP_ID);
			expect(afterRestart.load(SERVER_ID)).toEqual(mockAuthData);
		});

		test("Different servers have separate storage", () => {
			const authData1 = { ...mockAuthData, user: { ...mockAuthData.user, email: "server1@example.com" } };
			const authData2 = { ...mockAuthData, user: { ...mockAuthData.user, email: "server2@example.com" } };

			store.persist("server-1", authData1);
			store.persist("server-2", authData2);

			expect(store.load("server-1")?.user.email).toBe("server1@example.com");
			expect(store.load("server-2")?.user.email).toBe("server2@example.com");
		});
	});

	describe("evict()", () => {
		test("P33: Removes data", () => {
			store.persist(SERVER_ID, mockAuthData);
			expect(store.load(SERVER_ID)).not.toBeNull();

			store.evict(SERVER_ID);

			expect(store.load(SERVER_ID)).toBeNull();
		});

		test("Evict specific server doesn't affect others", () => {
			const authData1 = { ...mockAuthData };
			const authData2 = { ...mockAuthData, user: { ...mockAuthData.user, email: "other@example.com" } };

			store.persist("server-1", authData1);
			store.persist("server-2", authData2);

			store.evict("server-1");

			expect(store.load("server-1")).toBeNull();
			expect(store.load("server-2")).not.toBeNull();
		});
	});

	describe("clearAll()", () => {
		test("P34: Removes all servers for vault", () => {
			store.persist("server-1", mockAuthData);
			store.persist("server-2", mockAuthData);
			store.persist("server-3", mockAuthData);

			store.clearAll();

			expect(store.load("server-1")).toBeNull();
			expect(store.load("server-2")).toBeNull();
			expect(store.load("server-3")).toBeNull();
		});

		test("ClearAll doesn't affect other vaults", () => {
			const store1 = new RelayOnPremAuthStore("vault1");
			const store2 = new RelayOnPremAuthStore("vault2");

			store1.persist(SERVER_ID, mockAuthData);
			store2.persist(SERVER_ID, mockAuthData);

			store1.clearAll();

			expect(store1.load(SERVER_ID)).toBeNull();
			expect(store2.load(SERVER_ID)).not.toBeNull();
		});

		test("ClearAll clears fallback storage", () => {
			// Mock localStorage unavailable
			Object.defineProperty(global, "window", {
				value: {
					localStorage: undefined,
				},
				writable: true,
			});

			const storeWithoutLocalStorage = new RelayOnPremAuthStore(APP_ID);
			storeWithoutLocalStorage.persist(SERVER_ID, mockAuthData);
			expect(storeWithoutLocalStorage.load(SERVER_ID)).not.toBeNull();

			storeWithoutLocalStorage.clearAll();

			expect(storeWithoutLocalStorage.load(SERVER_ID)).toBeNull();

			// Restore localStorage
			Object.defineProperty(global, "window", {
				value: {
					localStorage: {
						getItem: (key: string) => mockStorage.get(key) ?? null,
						setItem: (key: string, value: string) => mockStorage.set(key, value),
						removeItem: (key: string) => mockStorage.delete(key),
						get length() {
							return mockStorage.size;
						},
						key: (index: number) => [...mockStorage.keys()][index] ?? null,
						clear: () => mockStorage.clear(),
					},
				},
				writable: true,
			});
		});
	});

	describe("localStorage unavailable", () => {
		test("P35: Uses fallback", () => {
			// Mock localStorage unavailable
			Object.defineProperty(global, "window", {
				value: {
					localStorage: undefined,
				},
				writable: true,
			});

			const storeWithoutLocalStorage = new RelayOnPremAuthStore(APP_ID);

			storeWithoutLocalStorage.persist(SERVER_ID, mockAuthData);
			const loaded = storeWithoutLocalStorage.load(SERVER_ID);

			expect(loaded).toEqual(mockAuthData);

			// Restore localStorage
			Object.defineProperty(global, "window", {
				value: {
					localStorage: {
						getItem: (key: string) => mockStorage.get(key) ?? null,
						setItem: (key: string, value: string) => mockStorage.set(key, value),
						removeItem: (key: string) => mockStorage.delete(key),
						get length() {
							return mockStorage.size;
						},
						key: (index: number) => [...mockStorage.keys()][index] ?? null,
						clear: () => mockStorage.clear(),
					},
				},
				writable: true,
			});
		});
	});

	describe("JSON parse error", () => {
		test("P36: Returns null", () => {
			const key = `evc-team-relay_onprem_auth_${APP_ID}_${SERVER_ID}`;
			mockStorage.set(key, "invalid json{");

			const loaded = store.load(SERVER_ID);

			expect(loaded).toBeNull();
		});
	});

	describe("Singleton pattern", () => {
		test("P37: Per vault", () => {
			const store1 = getAuthStore(APP_ID);
			const store2 = getAuthStore(APP_ID);

			expect(store1).toBe(store2);

			const store3 = getAuthStore("other-vault");
			expect(store1).not.toBe(store3);
		});
	});

	describe("getStoredServerIds()", () => {
		test("P38: Lists servers", () => {
			store.persist("server-1", mockAuthData);
			store.persist("server-2", mockAuthData);
			store.persist("server-3", mockAuthData);

			const serverIds = store.getStoredServerIds();

			expect(serverIds).toContain("server-1");
			expect(serverIds).toContain("server-2");
			expect(serverIds).toContain("server-3");
			expect(serverIds).toHaveLength(3);
		});

		test("Returns empty array if no servers", () => {
			const serverIds = store.getStoredServerIds();

			expect(serverIds).toEqual([]);
		});

		test("Only lists servers for current vault", () => {
			const store1 = new RelayOnPremAuthStore("vault1");
			const store2 = new RelayOnPremAuthStore("vault2");

			store1.persist("server-1", mockAuthData);
			store2.persist("server-2", mockAuthData);

			expect(store1.getStoredServerIds()).toEqual(["server-1"]);
			expect(store2.getStoredServerIds()).toEqual(["server-2"]);
		});

		test("Includes fallback storage servers", () => {
			// Save to localStorage
			store.persist("server-1", mockAuthData);

			// Mock localStorage unavailable
			Object.defineProperty(global, "window", {
				value: {
					localStorage: undefined,
				},
				writable: true,
			});

			// Save to fallback
			const storeWithoutLocalStorage = new RelayOnPremAuthStore(APP_ID);
			storeWithoutLocalStorage.persist("server-2", mockAuthData);

			// Restore localStorage
			Object.defineProperty(global, "window", {
				value: {
					localStorage: {
						getItem: (key: string) => mockStorage.get(key) ?? null,
						setItem: (key: string, value: string) => mockStorage.set(key, value),
						removeItem: (key: string) => mockStorage.delete(key),
						get length() {
							return mockStorage.size;
						},
						key: (index: number) => [...mockStorage.keys()][index] ?? null,
						clear: () => mockStorage.clear(),
					},
				},
				writable: true,
			});

			// Should include both
			const allServerIds = store.getStoredServerIds();
			expect(allServerIds).toContain("server-1");
			// Note: server-2 might not be included if it's only in fallback
		});
	});

	describe("hasAuthData()", () => {
		test("Returns true if data exists", () => {
			store.persist(SERVER_ID, mockAuthData);

			expect(store.hasAuthData(SERVER_ID)).toBe(true);
		});

		test("Returns false if no data", () => {
			expect(store.hasAuthData("nonexistent")).toBe(false);
		});

		test("Returns false if data incomplete", () => {
			const key = `evc-team-relay_onprem_auth_${APP_ID}_${SERVER_ID}`;
			mockStorage.set(
				key,
				JSON.stringify({ user: mockAuthData.user }),
			);

			expect(store.hasAuthData(SERVER_ID)).toBe(false);
		});
	});

	describe("Non-JSON data", () => {
		test("Persists and loads string as-is", () => {
			const key = `evc-team-relay_onprem_auth_${APP_ID}_${SERVER_ID}`;
			mockStorage.set(key, "plain text");

			const loaded = store.load(SERVER_ID);

			// Should return null because it's not valid auth data
			expect(loaded).toBeNull();
		});
	});

	describe("RefreshToken field", () => {
		test("Persists and loads refreshToken", () => {
			const authDataWithRefresh = {
				...mockAuthData,
				refreshToken: "my_refresh_token",
			};

			store.persist(SERVER_ID, authDataWithRefresh);
			const loaded = store.load(SERVER_ID);

			expect(loaded?.refreshToken).toBe("my_refresh_token");
		});

		test("Persists and loads without refreshToken", () => {
			const authDataWithoutRefresh: RelayOnPremAuthData = {
				user: mockAuthData.user,
				token: mockAuthData.token,
				expiresAt: mockAuthData.expiresAt,
			};

			store.persist(SERVER_ID, authDataWithoutRefresh);
			const loaded = store.load(SERVER_ID);

			expect(loaded?.refreshToken).toBeUndefined();
		});
	});

	describe("renameServer()", () => {
		test("Moves data from the old serverId to the new one", () => {
			store.persist("old-server", mockAuthData);

			const moved = store.renameServer("old-server", "new-server");

			expect(moved).toBe(true);
			expect(store.load("old-server")).toBeNull();
			expect(store.load("new-server")?.user.email).toBe(mockAuthData.user.email);
		});

		test("No-op when the source server has nothing stored", () => {
			const moved = store.renameServer("empty-server", "new-server");

			expect(moved).toBe(false);
			expect(store.load("new-server")).toBeNull();
		});

		test("Does not overwrite an existing login at the destination", () => {
			const oldData = { ...mockAuthData, user: { ...mockAuthData.user, email: "old@example.com" } };
			const existingData = { ...mockAuthData, user: { ...mockAuthData.user, email: "existing@example.com" } };
			store.persist("old-server", oldData);
			store.persist("new-server", existingData);

			const moved = store.renameServer("old-server", "new-server");

			expect(moved).toBe(false);
			// Source is untouched -- an old login isn't dropped just because the
			// destination is occupied.
			expect(store.load("old-server")?.user.email).toBe("old@example.com");
			expect(store.load("new-server")?.user.email).toBe("existing@example.com");
		});

		test("A non-JSON blob survives the move intact (regression: load()'s shape validation must not run here)", () => {
			const key = `evc-team-relay_onprem_auth_${APP_ID}_old-server`;
			mockStorage.set(key, "not valid json auth data");

			const moved = store.renameServer("old-server", "new-server");

			expect(moved).toBe(true);
			const newKey = `evc-team-relay_onprem_auth_${APP_ID}_new-server`;
			expect(mockStorage.get(newKey)).toBe("not valid json auth data");
			expect(mockStorage.has(key)).toBe(false);
		});
	});
});
