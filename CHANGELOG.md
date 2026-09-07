# Changelog

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
