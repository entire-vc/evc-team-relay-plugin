# Changelog

## 0.0.16
- Fixed: every edit to an existing note that arrived from another device created an extra "note (relay conflict …).md" copy next to it, and the copies spread to all participants of the share. The delivered text is now recorded as the last synced state, so only a real two-sided conflict produces a copy. Copies that already exist are ordinary files and are not removed; on the first delivered edit of each document after updating, one more copy can still appear.

## 0.0.15
- Improved: while Obsidian waits for you to sign in through the browser, the server card now shows a status line with "Cancel" and "Sign in with password" buttons, instead of only a short notification. Choosing the password option opens the password form right away.

## 0.0.14
- Fixed: an edit to an existing note could revert on your own device a few seconds after you made it, shortly after Obsidian was restarted on another device, and never reach that device. The edit is now kept and uploaded.

## 0.0.13
- Fixed: after restarting Obsidian, a shared folder could stay stuck loading on the second device, so files created on the other device never appeared there. A leftover user record in the shared document no longer breaks loading of the local copy.

## 0.0.12
- Fixed: a folder share you had just created never synced its content. The local storage layer did not finish loading, so files in the folder were never picked up and nothing reached the server.
- Fixed: the file selected when creating a share could be left unsynced if the first sync took longer than expected.

## 0.0.11
- You can now share your vault's root folder, not just subfolders — previously this silently failed to sync anything (#1).

## 0.0.10
- Client now sends its own plugin version (`manifest.version`) with every relay token request. The control-plane records it in the token-issuance audit log — previously the only version signal available was the Obsidian/Electron app version from User-Agent, not the plugin's, making it impossible to tell which release issued a given token during an auth-failure investigation (#75491f2f follow-up).

## 0.0.9
- Fixed a race in the credential cache that could hand a reconnecting WebSocket a token with only seconds left before expiry, causing an `invalid_token` auth failure on the handshake. The cache now honors the same renewal margin the periodic refresh sweep already used, instead of only checking literal expiry.

## 0.0.8
- Minimum Obsidian version lowered back to 1.8.7 (it had drifted up to 1.13.0 in 0.0.3). The five destructive buttons in share management now use `setWarning()` instead of the newer `setDestructive()` — same red-button look, works on older Obsidian.

## 0.0.7
- Debug/info/warn/error console log lines are now prefixed `[Relay]` instead of a stale internal tag left over from an earlier build.

## 0.0.6
- Local document storage and the realtime connection layer are now our own implementations, replacing two third-party modules that were vendored into the source tree. Behaviour is unchanged; the plugin ships less code it does not own.
- The last share and login calls still using the server's deprecated unversioned routes now use the current `/v1` API, like every other call already did. No server-side change is needed: `/v1` has been served since the first release.

## 0.0.5
- Sync-conflict toast no longer piles up forever: it now dedups per (local hash, server hash), auto-dismisses after 8s, and re-fires only when the conflict actually changes.
- New command "Team Relay: Show sync conflicts" lists unresolved conflicts and lets you resolve each one — take the server version or keep local.
- The "file deleted but its web share is still published" toast got the same non-eternal treatment, plus an inline Unpublish action.

## 0.0.4
- Interface translation extended to the rest of the plugin: server list, its buttons and toasts, publish/share flows, and error messages — Russian and English, with English as the fallback for unsupported system languages.
- Cross-server 401 errors in the login modal now explain the cause instead of a generic auth failure.
- Folder publish no longer aborts entirely when one file in it can't be published — the rest of the folder still goes out.
- Per-server branding logo now renders in the server list, with a fallback when none is set.
- Settings header no longer wraps awkwardly and the breadcrumb no longer shows an empty segment at narrow (393px) widths.
- CI: package-lock.json version consistency is now enforced on GitHub Actions too, and CHANGELOG.md is checked against manifest.json's version on every push to main.

## 0.0.3
- Declares `minAppVersion` 1.13.0.

## 0.0.2
- UI-language mechanism, with English interface strings extracted as the first translatable set.
- Team Relay RU added as a second built-in server, offered by default on new installs.
- Built-in servers can no longer be deleted.
- Remaining Obsidian community-directory validator warnings (S1-S7) addressed.

## 0.0.1
- First release.
