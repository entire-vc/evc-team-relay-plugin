/**
 * The plugin's own copy, one language at a time.
 *
 * `englishPhrasebook` is the single source of truth for every user-visible
 * string this MR moved out of a call site -- each value here was copied
 * BYTE FOR BYTE from wherever it used to live (see
 * `scripts/check-i18n-string-parity.py` for the automated proof). This MR
 * (i18n mechanism, Mesh #bac8b7dd, MR1 of 2) does not add a second language:
 * `phrasebooksByLanguage` only ever holds `en` here. A `ru` phrasebook is a
 * separate follow-up MR gated on Pavel approving the wording list first
 * (CLAUDE-workflow §1r.A) -- when it lands, it's a second entry in
 * `phrasebooksByLanguage` below, nothing else about this module changes.
 *
 * Placeholders use `{name}` (not printf `%s`, not ICU `{name, plural, ...}`)
 * -- see `uiText.ts` for the substitution rule. Keys are flat, dot-namespaced
 * strings grouped by the screen they render on; `shared.*` holds text that
 * is byte-identical across more than one screen (collapsed on purpose --
 * see the task's dedup note on "Create Share" appearing verbatim in three
 * files).
 */

export const englishPhrasebook = {
	// Shared across screens -- identical English text, one entry.
	"shared.cancelButton": "Cancel",
	"shared.viewerOption": "Viewer",
	"shared.editorOption": "Editor",
	"shared.createShareButton": "Create Share",
	"shared.creatingEllipsis": "Creating...",
	"shared.passwordLabel": "Password",
	"shared.passwordRequiredNotice": "Password is required for protected shares",
	"shared.unknownError": "Unknown error",
	"shared.failedNotice": "Failed: {error}",
	"shared.emailPlaceholder": "user@example.com",
	"shared.noExpiration": "No expiration",
	"shared.noShareClientError": "No share client available",

	// Connect screen -- src/ui/RelayOnPremLoginModal.ts
	"connect.login.title": "Relay on-premise login",
	"connect.login.emailLabel": "Email",
	"connect.login.passwordPlaceholder": "Enter your password",
	"connect.login.loginButton": "Login",
	"connect.login.loggingIn": "Logging in...",
	"connect.login.orSignInWith": "Or sign in with:",
	"connect.login.ssoUnavailableMobile": "SSO sign-in isn't available on mobile yet — use the desktop app, or sign in with email and password if your account has one.",
	"connect.login.successNotice": "Successfully logged in to relay-onprem!",
	"connect.login.oauthSuccessNotice": "Successfully logged in with {provider}!",
	"connect.login.loginFailedFallback": "Login failed",
	"connect.login.incorrectCredentials": "Incorrect email or password",
	"connect.login.invalidLoginData": "Invalid login data. Please check your email and password.",
	"connect.login.networkError": "Network error. Please check your connection and control plane URL.",
	"connect.login.emailRequired": "Please enter your email",
	"connect.login.passwordRequired": "Please enter your password",
	"connect.login.invalidEmail": "Please enter a valid email address",
	"connect.login.passwordTooShort": "Password must be at least 8 characters",
	"connect.login.oauthFailedFallback": "OAuth login failed",
	"connect.login.oauthTimeout": "Login timeout. Please try again.",
	"connect.login.oauthCannotOpenBrowser": "Unable to open browser. Please try manual login.",

	// Plugin shell -- src/components/RelayOnPremSettings.svelte
	"shell.header.title": "Team Relay",
	"shell.header.desc": "Self-hosted relay for real-time collaboration",
	"shell.header.githubTooltip": "GitHub",
	"shell.header.bugReportTooltip": "Bug report",
	"shell.header.featureRequestTooltip": "Feature request",
	"shell.header.webPublishTooltip": "Web publish issue",
	"shell.header.docsCta": "Documentation",
	"shell.header.mcpCta": "MCP server",
	"shell.header.meshCta": "Mesh",
	"shell.servers.heading": "Relay Servers",
	"shell.servers.desc": 'Configure your relay-onprem servers. Click "Shares" to manage shares.',
	"shell.breadcrumb.planUsage": "Plan & Usage",
	"shell.breadcrumb.createInvite": "Create Invite",
	"shell.breadcrumb.agentKeys": "Agent Keys",

	// Share list -- src/components/ShareListView.svelte
	"shareList.title": "Shares on {serverName}",
	"shareList.loading": "Loading shares...",
	"shareList.empty": "No shares yet. Create your first share to get started!",
	"shareList.noServerError": "Please add a server and log in first.",
	"shareList.loadFailedFallback": "Failed to load shares",

	// Share detail card -- src/components/ShareDetailView.svelte
	"shareDetail.loading": "Loading share details...",
	"shareDetail.loadFailedNotice": "Failed to load share details: {error}",
	"shareDetail.copyIdButton": "Copy ID",
	"shareDetail.idCopiedNotice": "Share ID copied",

	"shareDetail.localFolder.heading": "Local Folder",
	"shareDetail.localFolder.connectedStatus": "Connected and syncing",
	"shareDetail.localFolder.notConnectedStatus": "Not connected to a local folder",
	"shareDetail.localFolder.disconnectButton": "Disconnect",
	"shareDetail.localFolder.connectButton": "Connect to local folder",
	"shareDetail.localFolder.pickerTitle": "Choose local folder for this share...",
	"shareDetail.localFolder.connectedNotice": "Folder connected! Syncing...",
	"shareDetail.localFolder.connectFailedNotice": "Failed to connect folder: {error}",
	"shareDetail.localFolder.disconnectConfirm":
		'Disconnect local folder "{path}" from this share? Local files will not be deleted.',
	"shareDetail.localFolder.disconnectedNotice": "Folder disconnected",

	"shareDetail.members.heading": "Members",
	"shareDetail.members.empty": "No members yet.",
	"shareDetail.members.addButton": "Add",
	"shareDetail.members.removeButton": "Remove",
	"shareDetail.members.emailRequiredNotice": "Please enter a user email",
	"shareDetail.members.addedNotice": "Member added",
	"shareDetail.members.limitReachedNotice":
		"Member limit reached ({current}/{max} on {plan} plan). Upgrade your plan to add more members.",
	"shareDetail.members.addFailedFallback": "Failed to add member",
	"shareDetail.members.roleChangedNotice": "Role changed to {role}",
	"shareDetail.members.roleChangeFailedNotice": "Failed to change role: {error}",
	"shareDetail.members.removedNotice": "Member removed",
	"shareDetail.members.removeFailedNotice": "Failed to remove member: {error}",

	"shareDetail.invites.heading": "Invite Links",
	"shareDetail.invites.createButton": "Create Invite",
	"shareDetail.invites.empty": "No active invite links.",
	"shareDetail.invites.roleSuffix": "{role} invite",
	"shareDetail.invites.copyLinkButton": "Copy Link",
	"shareDetail.invites.linkCopiedNotice": "Invite link copied!",
	"shareDetail.invites.revokeButton": "Revoke",
	"shareDetail.invites.revokeConfirm": "Revoke this invite link?",
	"shareDetail.invites.revokedNotice": "Invite revoked",
	"shareDetail.invites.revokeFailedNotice": "Failed to revoke invite: {error}",
	"shareDetail.invites.expiredTag": "EXPIRED",
	"shareDetail.invites.maxUsesReachedTag": "MAX USES REACHED",
	"shareDetail.invites.expiresLabel": "Expires: {date}",
	"shareDetail.invites.usesWithMax": "Uses: {used}/{max}",
	"shareDetail.invites.usesNoMax": "Uses: {used}",

	"shareDetail.agentKeys.manageButton": "Manage",
	"shareDetail.agentKeys.desc": "API keys for automated agents to access this share without your login credentials.",

	"shareDetail.webPublish.heading": "Web Publishing",
	"shareDetail.webPublish.publishLabel": "Publish to Web",
	"shareDetail.webPublish.webUrlLabel": "Web URL",
	"shareDetail.webPublish.copyButton": "Copy",
	"shareDetail.webPublish.openButton": "Open",
	"shareDetail.webPublish.urlCopiedNotice": "URL copied!",
	"shareDetail.webPublish.syncContentLabel": "Sync Content",
	"shareDetail.webPublish.syncNowButton": "Sync Now",
	"shareDetail.webPublish.allowSearchEnginesLabel": "Allow search engines",
	"shareDetail.webPublish.syncModeLabel": "Sync Mode",
	"shareDetail.webPublish.manualOption": "Manual",
	"shareDetail.webPublish.autoOption": "Auto",
	"shareDetail.webPublish.webSlugLabel": "Web Slug",
	"shareDetail.webPublish.webSlugPlaceholder": "my-document",
	"shareDetail.webPublish.saveButton": "Save",
	"shareDetail.webPublish.contentSyncedNotice": "Content synced!",
	"shareDetail.webPublish.syncedFilesNotice": "Synced {count} files",
	"shareDetail.webPublish.folderSyncedNotice": "Folder synced: {count} items",
	"shareDetail.webPublish.couldNotReadDocumentNotice": "Could not read document",
	"shareDetail.webPublish.folderEmptyNotice": "Folder empty",
	"shareDetail.webPublish.syncFailedNotice": "Failed to sync: {error}",
	"shareDetail.webPublish.indexingDisabledNotice": "Indexing disabled",
	"shareDetail.webPublish.indexingEnabledNotice": "Indexing enabled",
	"shareDetail.webPublish.autoSyncEnabledNotice": "Auto-sync enabled",
	"shareDetail.webPublish.autoSyncDisabledNotice": "Auto-sync disabled",
	"shareDetail.webPublish.syncModeNotice": "Sync mode: {mode}",
	"shareDetail.webPublish.slugUpdatedNotice": "Slug updated: {slug}",
	"shareDetail.webPublish.publishedNotice": "Published to web!",
	"shareDetail.webPublish.unpublishedNotice": "Unpublished from web",
	"shareDetail.webPublish.privatePublishPrompt":
		'This share is private. Web publishing requires "public" or "protected" visibility. Choose how you want to publish:',
	"shareDetail.webPublish.makePublicChoice": "Make public (open access)",
	"shareDetail.webPublish.makeProtectedChoice": "Make protected (password)",
	"shareDetail.webPublish.visibilityChangeFailedNotice": "Failed to change visibility",
	"shareDetail.webPublish.limitReachedNotice":
		"Web publish limit reached ({current}/{max} on {plan} plan). Upgrade your plan to publish more.",
	"shareDetail.webPublish.visibilityNotAllowedNotice":
		"'{visibility}' visibility requires a higher plan. Your plan allows: {allowed}. Upgrade to unlock.",

	"shareDetail.actions.heading": "Actions",
	"shareDetail.actions.changeVisibilityLabel": "Change Visibility",
	"shareDetail.actions.changeVisibilityDesc": "Control who can access this share",
	"shareDetail.actions.privateOption": "Private",
	"shareDetail.actions.publicOption": "Public",
	"shareDetail.actions.protectedOption": "Protected",
	"shareDetail.actions.deleteShareLabel": "Delete Share",
	"shareDetail.actions.deleteShareDesc": "Permanently delete this share",
	"shareDetail.actions.deleteButton": "Delete",
	"shareDetail.actions.passwordPrompt": "Enter password for protected share:",
	"shareDetail.actions.visibilityConfirm": "Change visibility to {visibility}?",
	"shareDetail.actions.visibilityChangedNotice": "Visibility changed to {visibility}",
	"shareDetail.actions.deleteConfirm": 'Delete "{path}"? This cannot be undone.',
	"shareDetail.actions.deletedNotice": "Share deleted",
	"shareDetail.actions.deleteFailedNotice": "Failed to delete: {error}",

	// Share creation -- src/components/CreateShareView.svelte
	"createShare.pickerTitle": "Choose folder for share...",
	"createShare.pathRequiredNotice": "Please select a folder path",
	"createShare.createdNotice": 'Share "{path}" created!',
	"createShare.limitReachedNotice":
		"Share limit reached ({current}/{max} on {plan} plan). Upgrade your plan to create more shares.",
	"createShare.createFailedNotice": "Failed to create share: {error}",
	"createShare.title": "Create New Share",
	"createShare.pathLabel": "Path",
	"createShare.choosePlaceholder": "Choose folder...",
	"createShare.typeLabel": "Type",
	"createShare.docOption": "Document",
	"createShare.folderOption": "Folder",
	"createShare.visibilityLabel": "Visibility",
	"createShare.privateVisibilityOption": "Private - Only members",
	"createShare.publicVisibilityOption": "Public - Anyone with link",
	"createShare.protectedVisibilityOption": "Protected - Password required",
	"createShare.passwordPlaceholder": "Enter password for protected share",

	// Invite creation -- src/components/CreateInviteView.svelte
	"createInvite.maxUsesInvalidNotice": "Max uses must be a positive number",
	"createInvite.createdNotice": "Invite link created!",
	"createInvite.createFailedNotice": "Failed to create invite: {error}",
	"createInvite.title": "Create Invite Link",
	"createInvite.forLabel": "for {path}",
	"createInvite.roleLabel": "Role",
	"createInvite.expirationLabel": "Expiration",
	"createInvite.expires7Days": "7 days",
	"createInvite.expires14Days": "14 days",
	"createInvite.expires30Days": "30 days",
	"createInvite.maxUsesLabel": "Max Uses (optional)",
	"createInvite.unlimitedPlaceholder": "Unlimited",
	"createInvite.createButton": "Create Invite Link",
} as const satisfies Record<string, string>;

/** Every key the phrasebook defines -- the only valid input to `uiText()`. */
export type PhraseKey = keyof typeof englishPhrasebook;

/**
 * A phrasebook doesn't have to cover every key -- `uiText()` falls back to
 * `englishPhrasebook` for anything missing, so a partial (in-progress or
 * community-contributed) translation degrades to English per-string rather
 * than failing whole.
 */
export type Phrasebook = Partial<Record<PhraseKey, string>>;

/**
 * Every phrasebook this build ships, keyed by the ISO code
 * `resolveInterfaceLanguage()` returns. `en` is required and complete (it's
 * the type `englishPhrasebook` itself was declared with); everything else is
 * optional. Only `en` exists as of this MR -- see the module doc comment.
 */
export const phrasebooksByLanguage: Record<string, Phrasebook> = {
	en: englishPhrasebook,
};
