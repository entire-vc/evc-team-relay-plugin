# Changelog

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
