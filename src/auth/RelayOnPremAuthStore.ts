/**
 * Relay On-Premise Authentication Store
 *
 * Persists authentication state to localStorage so that users remain logged in
 * across Obsidian restarts. Supports multiple servers with independent auth state.
 *
 * Uses singleton pattern per vault instance (keyed by Obsidian's stable `app.appId`,
 * NOT the user-editable vault name) to prevent race conditions when multiple
 * providers access storage simultaneously.
 */

import { namedLogger } from "../logging";
import type { AuthUser } from "./IAuthProvider";

export interface RelayOnPremAuthData {
	user: AuthUser;
	token: string;
	expiresAt: number;
	refreshToken?: string;
}

/**
 * Singleton instances per vault appId to ensure consistent storage access
 */
const authStoreInstances: Map<string, RelayOnPremAuthStore> = new Map();

/**
 * Get or create a singleton AuthStore instance for the given vault (by appId).
 * This prevents multiple providers from creating separate instances with
 * separate fallback storage, which could cause auth loss.
 */
export function getAuthStore(appId: string): RelayOnPremAuthStore {
	if (!authStoreInstances.has(appId)) {
		authStoreInstances.set(appId, new RelayOnPremAuthStore(appId));
	}
	return authStoreInstances.get(appId)!;
}

export class RelayOnPremAuthStore {
	private log = namedLogger("[RelayOnPremAuthStore]");
	private memoryFallback: { [key: string]: unknown } = {};
	private appId: string;
	private static readonly MAX_RETRY_ATTEMPTS = 3;
	private static readonly RETRY_DELAY_MS = 50;

	constructor(appId: string) {
		this.appId = appId;
		this.log(`Initialized for vault appId: ${appId}`);
	}

	/**
	 * Get storage key for a specific server
	 */
	private getStorageKey(serverId: string): string {
		return `evc-team-relay_onprem_auth_${this.appId}_${serverId}`;
	}

	/**
	 * Get storage key prefix for listing all server keys
	 */
	private getStorageKeyPrefix(): string {
		return `evc-team-relay_onprem_auth_${this.appId}_`;
	}

	/**
	 * Save authentication data to localStorage for a specific server
	 */
	persist(serverId: string, authData: RelayOnPremAuthData): void {
		this._writeStorage(this.getStorageKey(serverId), authData);
	}

	/**
	 * Load authentication data from localStorage for a specific server
	 */
	load(serverId: string): RelayOnPremAuthData | null {
		const key = this.getStorageKey(serverId);
		this.log(`load: serverId=${serverId}, key=${key}`);

		const data = this._readStorage(key) as RelayOnPremAuthData | null | undefined;

		if (!data) {
			this.log(`load: no data found for key=${key}`);
			return null;
		}

		if (!data.user || !data.token || !data.expiresAt) {
			this.log(`load: incomplete data - user=${!!data.user}, token=${!!data.token}, expiresAt=${!!data.expiresAt}`);
			return null;
		}

		this.log(`load: successfully loaded auth for user=${data.user?.email}`);
		return data;
	}

	/**
	 * Clear authentication data from localStorage for a specific server
	 */
	evict(serverId: string): void {
		this._deleteStorage(this.getStorageKey(serverId));
	}

	/**
	 * Move stored auth data from one serverId to another (server-rename migration).
	 * Verbatim: the payload is not parsed or shape-validated, so a partially written
	 * or corrupt blob is relocated rather than silently dropped -- unlike load(),
	 * which validates shape and would drop anything incomplete.
	 * No-op returning false if `fromServerId` holds nothing, or if `toServerId`
	 * already holds data -- an existing login is never overwritten.
	 */
	renameServer(fromServerId: string, toServerId: string): boolean {
		const fromKey = this.getStorageKey(fromServerId);
		const toKey = this.getStorageKey(toServerId);

		const fromData = this._readStorage(fromKey);
		if (fromData === undefined) {
			return false;
		}
		if (this._readStorage(toKey) !== undefined) {
			return false;
		}

		this._writeStorage(toKey, fromData);
		this._deleteStorage(fromKey);
		return true;
	}

	/**
	 * Clear all authentication data for all servers
	 */
	clearAll(): void {
		const prefix = this.getStorageKeyPrefix();
		if (typeof window !== "undefined" && window?.localStorage) {
			const keysToRemove: string[] = [];
			for (let i = 0; i < window.localStorage.length; i++) {
				const key = window.localStorage.key(i);
				if (key && key.startsWith(prefix)) {
					keysToRemove.push(key);
				}
			}
			for (const key of keysToRemove) {
				window.localStorage.removeItem(key);
			}
		}
		// Clear fallback storage for this prefix
		for (const key of Object.keys(this.memoryFallback)) {
			if (key.startsWith(prefix)) {
				delete this.memoryFallback[key];
			}
		}
	}

	/**
	 * Check if there's valid auth data in storage for a specific server
	 */
	hasAuthData(serverId: string): boolean {
		const data = this.load(serverId);
		return data !== null;
	}

	/**
	 * Get list of all server IDs that have stored auth data
	 */
	getStoredServerIds(): string[] {
		const prefix = this.getStorageKeyPrefix();
		const serverIds: string[] = [];

		if (typeof window !== "undefined" && window?.localStorage) {
			for (let i = 0; i < window.localStorage.length; i++) {
				const key = window.localStorage.key(i);
				if (key && key.startsWith(prefix)) {
					const serverId = key.substring(prefix.length);
					if (serverId) {
						serverIds.push(serverId);
					}
				}
			}
		}

		// Also check fallback storage
		for (const key of Object.keys(this.memoryFallback)) {
			if (key.startsWith(prefix)) {
				const serverId = key.substring(prefix.length);
				if (serverId && !serverIds.includes(serverId)) {
					serverIds.push(serverId);
				}
			}
		}

		return serverIds;
	}

	// ---------------------------------------------------------------
	// Internal helpers: local-storage access with retry, because early in
	// Obsidian startup the store can briefly refuse reads.
	// ---------------------------------------------------------------

	/**
	 * Retrieves `key` from the browser's local storage
	 * (or runtime/memory if local storage is undefined).
	 *
	 * Includes retry logic to handle cases where localStorage might be
	 * temporarily unavailable during Obsidian startup.
	 */
	private _readStorage(key: string): unknown {
		const hasLocalStorage = typeof window !== "undefined" && window?.localStorage;
		this.log(`_readStorage: key=${key}, hasLocalStorage=${String(!!hasLocalStorage)}`);

		if (hasLocalStorage) {
			// Try with retries in case localStorage is temporarily unavailable
			for (let attempt = 0; attempt < RelayOnPremAuthStore.MAX_RETRY_ATTEMPTS; attempt++) {
				try {
					const rawValue = window.localStorage.getItem(key);
					this.log(`_readStorage: attempt=${attempt + 1}, rawValue exists=${!!rawValue}, length=${rawValue?.length ?? 0}`);

					if (!rawValue) {
						// Check fallback in case it was stored there previously
						if (this.memoryFallback[key]) {
							this.log(`_readStorage: found in fallback, migrating to localStorage`);
							this._writeStorage(key, this.memoryFallback[key]);
							return this.memoryFallback[key];
						}
						return undefined;
					}

					try {
						const parsed: unknown = JSON.parse(rawValue) as unknown;
						return parsed;
					} catch {
						// not a json, return as-is
						return rawValue;
					}
				} catch (e: unknown) {
					this.log(`_readStorage: localStorage access failed, attempt ${attempt + 1}/${RelayOnPremAuthStore.MAX_RETRY_ATTEMPTS}: ${e instanceof Error ? e.message : String(e)}`);
					if (attempt < RelayOnPremAuthStore.MAX_RETRY_ATTEMPTS - 1) {
						// Small sync delay - we can't await in a sync function,
						// but for early startup issues this may help
						continue;
					}
				}
			}
		}

		// Fallback to memory storage
		this.log(`_readStorage: using fallback storage for key=${key}`);
		return this.memoryFallback[key];
	}

	/**
	 * Stores a new data in the browser's local storage
	 * (or runtime/memory if local storage is undefined).
	 */
	private _writeStorage(key: string, value: unknown) {
		const hasLocalStorage = typeof window !== "undefined" && window?.localStorage;
		this.log(`_writeStorage: key=${key}, hasLocalStorage=${String(!!hasLocalStorage)}`);

		if (hasLocalStorage) {
			try {
				// Deliberately `window.localStorage`, not Obsidian's plugin-data
				// API (`saveData()` / `data.json`): this store persists the auth
				// token, and `data.json` is a plugin SETTINGS file that users
				// routinely copy into vault-share/backup destinations along with
				// the rest of the vault -- a token living there would travel
				// with it. `localStorage` is scoped to the local browser/Electron
				// profile only, so it never gets swept up in that.
				const normalizedVal: string =
					typeof value === "string" ? value : JSON.stringify(value);
				window.localStorage.setItem(key, normalizedVal);
				this.log(`_writeStorage: successfully saved to localStorage`);

				// Also keep in fallback as backup
				this.memoryFallback[key] = value;
			} catch (e: unknown) {
				this.log(`_writeStorage: localStorage.setItem failed: ${e instanceof Error ? e.message : String(e)}`);
				// Store in fallback if localStorage fails
				this.memoryFallback[key] = value;
			}
		} else {
			// store in fallback
			this.log(`_writeStorage: using fallback storage`);
			this.memoryFallback[key] = value;
		}
	}

	/**
	 * Removes `key` from the browser's local storage and the runtime/memory.
	 */
	private _deleteStorage(key: string) {
		// delete from local storage
		if (typeof window !== "undefined" && window?.localStorage) {
			window.localStorage?.removeItem(key);
		}

		// delete from fallback
		delete this.memoryFallback[key];
	}
}
