/**
 * AuthSession Extensions for Relay On-Premise Support
 *
 * This module contains extension methods for AuthSession that add
 * relay-onprem authentication support while maintaining backward compatibility.
 *
 * Usage: Import these methods and use them in AuthSession when relay-onprem mode is enabled.
 */

import { Account } from "./Account";
import type { IAuthProvider } from "./auth/IAuthProvider";
import { namedLogger } from "./logging";

const log = namedLogger("[LoginManagerExt]");

/**
 * Login with email and password (relay-onprem mode)
 */
export async function loginWithEmailPassword(
	authProvider: IAuthProvider,
	email: string,
	password: string,
): Promise<Account> {
	log(`Logging in with email: ${email}`);

	try {
		const authResponse = await authProvider.loginWithPassword(email, password);

		const user = new Account(
			authResponse.user.id,
			authResponse.user.name || authResponse.user.email,
			authResponse.user.email,
			authResponse.user.picture || "",
			authResponse.token.token,
		);

		log(`Successfully logged in as ${user.emailAddress}`);
		return user;
	} catch (error: unknown) {
		log("Login error:", error);
		throw error;
	}
}

/**
 * Login with OAuth2 (relay-onprem mode)
 */
export async function loginWithOAuth2(
	authProvider: IAuthProvider,
	provider: string,
): Promise<Account> {
	log(`Logging in with OAuth2 provider: ${provider}`);

	try {
		const authResponse = await authProvider.loginWithOAuth2(provider);

		const user = new Account(
			authResponse.user.id,
			authResponse.user.name || authResponse.user.email,
			authResponse.user.email,
			authResponse.user.picture || "",
			authResponse.token.token,
		);

		log(`Successfully logged in as ${user.emailAddress}`);
		return user;
	} catch (error: unknown) {
		log("OAuth2 login error:", error);
		throw error;
	}
}

/**
 * Refresh authentication token
 */
export async function refreshAuthToken(authProvider: IAuthProvider): Promise<Account> {
	log("Refreshing auth token...");

	try {
		const authResponse = await authProvider.refreshToken();

		const user = new Account(
			authResponse.user.id,
			authResponse.user.name || authResponse.user.email,
			authResponse.user.email,
			authResponse.user.picture || "",
			authResponse.token.token,
		);

		log("Token refreshed successfully");
		return user;
	} catch (error: unknown) {
		log("Token refresh error:", error);
		throw error;
	}
}

/**
 * Logout user
 */
export async function logoutUser(authProvider: IAuthProvider): Promise<void> {
	log("Logging out...");

	try {
		await authProvider.logout();
		log("Logged out successfully");
	} catch (error: unknown) {
		log("Logout error:", error);
		throw error;
	}
}

/**
 * Check if user is logged in
 */
export function isUserLoggedIn(authProvider: IAuthProvider): boolean {
	return authProvider.isLoggedIn();
}

/**
 * Decide what `AuthSession.user` should become after a login attempt
 * fails, given the value the field held immediately before the attempt
 * (TR-52 analog for `loginWithEmailAndPassword`, audit #96d804dd).
 *
 * The old behavior unconditionally cleared `this.user` on any login
 * failure — a failed RE-login (e.g. a typo'd password re-entered while
 * already logged in, for whatever reason) silently logged the user out of
 * a session that was working fine. Restoring the pre-attempt snapshot
 * fixes this: when there was no prior session (`previousUser` is
 * `undefined`), the restored value is `undefined` too, reproducing the old
 * (correct-in-that-case) behavior; when there was one, it survives the
 * failed attempt instead of being wiped.
 *
 * Safe to call unconditionally (no `hadValidSession` branch needed) only
 * because `loginWithEmailAndPassword`'s try block is a single `await` — on
 * failure `this.user` was never mutated before the catch runs, so there's
 * no partial-mutation state to reconcile. Contrast
 * `RelayOnPremAuthProvider.loginWithPassword` (TR-52, #914c2b9d), which
 * restores several fields individually because its step 1 can succeed and
 * mutate state before its step 2 fails.
 */
export function resolveUserAfterFailedLogin<TUser>(
	previousUser: TUser | undefined,
): TUser | undefined {
	return previousUser;
}

/**
 * Get current user from auth provider
 */
export function getCurrentUserFromProvider(authProvider: IAuthProvider): Account | undefined {
	const authUser = authProvider.getCurrentUser();
	if (!authUser) {
		return undefined;
	}

	const token = authProvider.getToken();
	if (!token) {
		return undefined;
	}

	return new Account(
		authUser.id,
		authUser.name || authUser.email,
		authUser.email,
		authUser.picture || "",
		token,
	);
}

/**
 * Escapes every regex metacharacter in `value` so it is safe to interpolate
 * into a `new RegExp(...)` source string as a literal match (TR CodeQL
 * js/incomplete-sanitization + js/incomplete-hostname-regexp fix, PR #166).
 *
 * This is the ONE escaping helper for webview-intercept regex building —
 * every raw string (`.` in a hostname, `?`/`&` in a redirect URL, etc.)
 * interpolated into an intercept pattern must go through this, not a
 * partial escape (e.g. slash-only) that leaves other metacharacters live.
 */
export function escapeForRegExp(value: string): string {
	return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Builds `^<escaped base>.*?[?&]redirect_uri=(<escaped redirectUrl>|<escaped,
 * URI-encoded redirectUrl>)`, case-insensitive — matches a webview
 * navigation into a provider's auth page carrying our redirect back to
 * Obsidian, in either raw or percent-encoded form (providers aren't
 * consistent about which).
 *
 * `base` and `redirectUrl` are both passed RAW (never pre-escaped) —
 * `escapeForRegExp` runs on each here so there is exactly one place
 * metacharacters get neutralized. Previously `base` arrived pre-escaped
 * from two different (and differently incomplete) call-site escapes while
 * `redirectUrl` was interpolated unescaped; a literal `.` in either a
 * static provider hostname (`accounts.google.com`) or in `redirectUrl`
 * matched any character, so e.g. `accountsXgoogle.com` would also match.
 */
export function buildRedirectInterceptRegex(base: string, redirectUrl: string): RegExp {
	const escapedBase = escapeForRegExp(base);
	const escapedRedirect = escapeForRegExp(redirectUrl);
	const escapedRedirectEncoded = escapeForRegExp(encodeURIComponent(redirectUrl));
	return new RegExp(
		`^${escapedBase}.*?[?&]redirect_uri=(${escapedRedirect}|${escapedRedirectEncoded})`,
		"i",
	);
}
