# Changelog

## 1.1.42
- Styling: CSS classes renamed from the upstream `system3-*` prefix to `evc-relay-*` (banner, folder icons, status pills, sync indicators, bug-report modal, etc.). If you have a custom CSS snippet targeting `.system3-*` selectors, it will stop matching — update it to `.evc-relay-*`.
- Privacy: the bug-report modal no longer sends reports to the upstream project's server (`bug-reports.system3.dev`) — it now copies the full report to your clipboard and opens a pre-filled GitHub issue on this repo instead, so you see exactly what's shared before it goes anywhere. Also fixed a bug present since the modal shipped: the "Include Logs" checkbox was cosmetic — debug logs were attached to every report regardless of its state.
- Security: bumped `js-yaml` across all three vendored copies (GHSA-5p4m-2wfm-xmqj).
- Sync (TR-15 follow-up): `netSync()` now awaits `addLocalDocs()` before reconciling the file tree, closing a stale-tree race.
- Share-link: compute diff offsets in UTF-16 code units instead of Unicode code points — fixes corruption on shared text containing surrogate-pair characters (e.g. emoji).
- Differ: whitespace-only line changes no longer lose their highlight.
- Types: `LocalStorage` iterator methods now declare `MapIterator` return types instead of `IterableIterator`, matching TS 5.6+'s `Map` typings.
- License: restored the upstream MIT attribution (No-Instructions/Relay) that had been silently dropped from `LICENSE`; the upstream notice now lives in `NOTICE`.
- Deps: `pocketbase` bumped to 0.27 (`LoginManager` migrated off the removed `authProviders`/`authUrl` API), `obsidian` API to 1.13.1, Node 20 → 22 LTS across CI/release, `eslint-plugin-obsidianmd` 0.4 migration, plus routine bumps to `jose`, `y-websocket`, `eventsource`, `uuid`, `diff`, `typescript`, and others.

## 1.1.41
- Sync (TR-15 follow-up): claim the vpath before upload to prevent a divergent-GUID race on first connect.

## 1.1.40
- Auth (TR-57): added a server version compatibility check at connect time.

## 1.1.39
- Sync (TR-15): idempotent initial-content claim prevents duplicated first-connect.
- Settings (TR-54): reject duplicate server on add.
- Auth (TR-55): clear stored auth when a server's URL changes.

## 1.1.38
- Network (TR-26): offline/online detection was dead in the EVC build (build-time `HEALTH_URL` was always empty) — the health-check URL is now derived at runtime from the active server's control-plane URL, with `NetworkStatus.updateUrl()` re-pointing it when the default server changes.
- Sync (TR-09): attachments (images/audio/video/pdf) never synced in live shares — `LiveTokenStore.fetchFileToken` now branches to the relay-onprem token provider the same way `refresh()` already does, and `requestFileToken` mints a presigned-URL token from the new control-plane `POST /shares/{id}/file-token` route (companion fix, control-plane PR #151).

## 1.1.37
- Sync (TR-08): `checkStale()` now actually detects divergence for relay-linked docs instead of always reporting "not stale" — the HTTP re-fetch is skipped for relay-linked docs (WebSocket sync is authoritative) but the real staleness comparison now runs, so the conflict-detection UI is no longer dead code on tr.entire.vc. (This fix was listed under 1.1.36 but did not make that build; it ships here.)

## 1.1.36
- Sync (TR-08): shipped in 1.1.37 (this build did not include the fix).
- Auth (TR-10): route OAuth2 login through `LoginManager` so listeners fire and shares load without a restart.
- Network (TR-12): reconnect retries forever with capped backoff instead of giving up after 3 attempts.
- Auth (TR-21): verify the OAuth callback `state` to close a session-fixation gap.
- Network (TR-29): `customFetch` no longer retries mutating requests on transient network errors (prevents duplicate writes).
- Shared folders (TR-30): reject nested shares in either direction.
- Sync (TR-41): retry initial awareness until synced instead of a single 2s attempt.
- Sync (TR-42): preserve unsynced edits before a remote-delete trashes a local file.
- Sync (TR-51): wait for the socket buffer to flush instead of a fixed 1000ms timer.
- Auth (TR-52): a failed re-login no longer clears an existing valid session.
- Auth (TR-53): persist `lastUserEmail` so it survives reload.
- Sync (TR-U4): don't echo inbound sync-artifact writes back out as local edits in the Document sync path.
- Sync (TR-25): wire the `isOutboundSyncing` echo-guard into the manual/full-sync paths too.
- Relay on-prem (TR-U3): fall back to a read-only token on 403 instead of hard-failing viewers.
- Auth (TR-56): key the relay-onprem auth session by `appId`, not the mutable vault name.
- Auth (TR-58): gate the legacy System3/PocketBase dead-code path with a clear error instead of a silent trap.

## 1.1.35
- Security (H3): added a path-traversal containment guard in `InboundFileDownloader` — a malicious or compromised relay server could otherwise supply a `relativePath` like `../../.obsidian/plugins/evil.js` in the files index and overwrite arbitrary vault files, including plugin JS and vault config. Traversal attempts are now logged and skipped; the rest of the batch continues processing.
- CI: scoped the manifest-version monotonicity guard to only run when a PR/push actually touches `manifest.json`/`package.json`/`versions.json` — previously it ran on every PR and permanently deadlocked any PR that didn't itself bump the version, once `main`'s version equaled the latest published release.

## 1.1.34
- Community review: removed unnecessary type assertions and switched `document` → `activeDocument` for popout-window compatibility (auto-fixed via eslint-plugin-obsidianmd typed lint)
- `SharedFolder`: bound the debounced `notifyListeners` to fix the unbound-method warning
- Replaced the `builtin-modules` package with Node's built-in `node:module` builtins (esbuild config)
- Marked the vendored `y-indexeddb` adapter's `no-unsafe-*` / unbound-method as intentional with a described eslint-disable

## 1.1.33
- Fix ESLint issues in test files and build scripts (no-restricted-imports, unused vars, empty blocks)
- Replace deprecated setWarning() with setDestructive() in ShareManagementModal
- Remove unused eslint-disable directives in MockTimeProvider
- Add CHANGELOG

## 1.1.32
- Fix forbidden eslint-disable directives on obsidianmd rules
- Fix ShareManagementModal UI text to sentence-case

## 1.1.31
- Fix all bare-timer usage (window.setTimeout/setInterval/clearTimeout/clearInterval)
- Fix activeDocument usage (replace bare document. references)
- Fix globalThis usage
- Fix CSS: remove !important, :has(), text-decoration rules
- Wire eslint-plugin-obsidianmd

## 1.1.30
- Initial community review fixes
