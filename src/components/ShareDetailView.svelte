<script lang="ts">
	import { onMount } from "svelte";
	import { Notice, Setting, TFile, TFolder } from "obsidian";
	import { createEventDispatcher } from "svelte";
	import type TeamRelayPlugin from "../main";
	import type { RelayOnPremServer } from "../RelayOnPremConfig";
	import type { ShareMember, Invite, WebFolderEntry } from "../RelayOnPremShareClient";
	import { LimitExceededApiError, VisibilityNotAllowedApiError } from "../RelayOnPremShareClient";
	import type { ShareWithServer } from "../RelayOnPremShareClientManager";
	import { FolderPathPickerModal } from "../ui/FolderPathPickerModal";
	import { confirmDialog, promptDialog, choiceDialog } from "../ui/dialogs";
	import { withOutboundSyncGuard } from "../WebSyncManager";
	import { sha256Hex } from "../contentDigest";

	export let live: TeamRelayPlugin;
	export let server: RelayOnPremServer;
	export let share: ShareWithServer;

	const dispatch = createEventDispatcher<{
		createInvite: void;
		deleted: void;
		back: void;
		agentKeys: void;
		updated: ShareWithServer;
	}>();

	let members: ShareMember[] = [];
	let invites: Invite[] = [];
	let isOwner = false;
	let loading = true;
	let webPublishEnabled = false;
	let webPublishDomain: string | null = null;
	let currentShare = share;
	let publishCheckboxEl: HTMLInputElement | undefined;

	// currentShare is a local working copy, mutated in place by
	// changeVisibility/toggleWebPublishing/renameSlug (#7c63f081). The parent
	// (RelayOnPremSettings) holds its own `selectedShare` reference used as
	// this component's `share` prop, and never learns about those local
	// mutations. Create Invite/cancel round-trips currentView away from
	// "shareDetail" and back, which destroys and recreates this component --
	// the fresh instance re-seeds `currentShare = share` from the parent's
	// now-stale copy, visually reverting a visibility/publish change that was
	// never actually undone server-side. Push every local update back up so
	// the parent's copy never falls behind.
	$: dispatch("updated", currentShare);

	// Svelte's `checked={isPublished}` binding only writes to the DOM when
	// the *computed* `isPublished` value actually differs from its previous
	// value ($$invalidate's own dirty-check, not something this component
	// controls) -- reassigning `currentShare` to a fresh object is not
	// enough by itself when the recomputed boolean ends up unchanged (e.g.
	// a failed publish attempt: isPublished was false, stays false). But the
	// checkbox's own native DOM `checked` already flipped from the click
	// itself, independently of the model, and Svelte has no way to know
	// that drift happened. Force the DOM back in line explicitly (#d425920b).
	function syncPublishCheckbox() {
		if (publishCheckboxEl) publishCheckboxEl.checked = currentShare.web_published ?? false;
	}

	// Add member form
	let newMemberEmail = "";
	let newMemberRole: "viewer" | "editor" = "editor";

	// Web slug editing
	let editingSlug = "";

	onMount(async () => {
		await loadDetails();
	});

	async function loadDetails() {
		loading = true;
		try {
			// Determine ownership
			const multiServerAuth = live.authSession.getMultiServerAuthManager();
			if (multiServerAuth) {
				const currentUser = multiServerAuth.getUserForServer(share.serverId);
				isOwner = currentUser?.id === share.owner_user_id;
			} else {
				const authProvider = live.authSession.getAuthProvider();
				const currentUser = authProvider?.getCurrentUser();
				isOwner = currentUser?.id === share.owner_user_id;
			}

			// Load all data in parallel
			const [serverInfo, membersResult, invitesResult] = await Promise.all([
				loadServerInfo(),
				loadMembers(),
				isOwner ? loadInvites() : Promise.resolve([]),
			]);

			webPublishEnabled = serverInfo?.features?.web_publish_enabled ?? false;
			webPublishDomain = serverInfo?.features?.web_publish_domain ?? null;
			members = membersResult;
			invites = invitesResult;
			editingSlug = currentShare.web_slug || "";
		} catch (e: unknown) {
			new Notice(`Failed to load share details: ${e instanceof Error ? e.message : "Unknown error"}`);
		} finally {
			loading = false;
		}
	}

	async function loadServerInfo() {
		try {
			if (live.shareClientManager) {
				const client = live.shareClientManager.getClient(share.serverId);
				if (client) return await client.getServerInfo();
			} else if (live.shareClient) {
				return await live.shareClient.getServerInfo();
			}
		} catch { /* server info optional */ }
		return null;
	}

	async function loadMembers(): Promise<ShareMember[]> {
		if (live.shareClientManager) {
			return live.shareClientManager.getShareMembers(share.serverId, share.id);
		} else if (live.shareClient) {
			return live.shareClient.getShareMembers(share.id);
		}
		return [];
	}

	async function loadInvites(): Promise<Invite[]> {
		try {
			if (live.shareClientManager) {
				return await live.shareClientManager.listInvites(share.serverId, share.id);
			} else if (live.shareClient) {
				return await live.shareClient.listInvites(share.id);
			}
		} catch (e: unknown) {
			const msg = e instanceof Error ? e.message : "";
			if (msg.includes("403") || msg.includes("Insufficient permissions")) {
				isOwner = false;
			} else {
				throw e;
			}
		}
		return [];
	}

	function copyId() {
		navigator.clipboard.writeText(currentShare.id);
		new Notice("Share ID copied");
	}

	// Members
	async function addMember() {
		if (!newMemberEmail.trim()) {
			new Notice("Please enter a user email");
			return;
		}
		try {
			let user;
			if (live.shareClientManager) {
				user = await live.shareClientManager.searchUserByEmail(share.serverId, newMemberEmail.trim());
				await live.shareClientManager.addMember(share.serverId, share.id, { user_id: user.id, role: newMemberRole });
			} else if (live.shareClient) {
				user = await live.shareClient.searchUserByEmail(newMemberEmail.trim());
				await live.shareClient.addMember(share.id, { user_id: user.id, role: newMemberRole });
			}
			new Notice("Member added");
			newMemberEmail = "";
			members = await loadMembers();
		} catch (e: unknown) {
			if (e instanceof LimitExceededApiError) {
				const info = e.limitInfo;
				new Notice(
					`Member limit reached (${info.current}/${info.max} on ${info.plan} plan). ` +
					`Upgrade your plan to add more members.`,
					8000,
				);
			} else {
				new Notice(e instanceof Error ? e.message : "Failed to add member");
			}
		}
	}

	// Svelte's template-expression parser doesn't accept TS `as` casts inline
	// in markup, so the <select> value (typed as plain `string` by the DOM
	// lib) is narrowed here in the <script> block instead of at the call site.
	function handleMemberRoleChange(userId: string, value: string) {
		changeMemberRole(userId, value as "viewer" | "editor");
	}

	async function changeMemberRole(userId: string, role: "viewer" | "editor") {
		try {
			if (live.shareClientManager) {
				await live.shareClientManager.updateMemberRole(share.serverId, share.id, userId, role);
			} else if (live.shareClient) {
				await live.shareClient.updateMemberRole(share.id, userId, role);
			}
			new Notice(`Role changed to ${role}`);
			members = await loadMembers();
		} catch (e: unknown) {
			new Notice(`Failed to change role: ${e instanceof Error ? e.message : "Unknown error"}`);
		}
	}

	async function removeMember(userId: string) {
		try {
			if (live.shareClientManager) {
				await live.shareClientManager.removeMember(share.serverId, share.id, userId);
			} else if (live.shareClient) {
				await live.shareClient.removeMember(share.id, userId);
			}
			new Notice("Member removed");
			members = await loadMembers();
		} catch (e: unknown) {
			new Notice(`Failed to remove member: ${e instanceof Error ? e.message : "Unknown error"}`);
		}
	}

	// Invites
	function getInviteDescription(invite: Invite): string {
		const isExpired = !!(invite.expires_at && new Date(invite.expires_at) < new Date());
		const isMaxed = invite.max_uses !== null && invite.use_count >= invite.max_uses;
		const parts: string[] = [];
		if (isExpired) parts.push("EXPIRED");
		else if (isMaxed) parts.push("MAX USES REACHED");
		if (invite.expires_at) {
			parts.push(`Expires: ${new Date(invite.expires_at).toLocaleDateString()}`);
		} else {
			parts.push("No expiration");
		}
		parts.push(invite.max_uses !== null ? `Uses: ${invite.use_count}/${invite.max_uses}` : `Uses: ${invite.use_count}`);
		return parts.join(" \u2022 ");
	}

	function isInviteValid(invite: Invite): boolean {
		const isExpired = !!(invite.expires_at && new Date(invite.expires_at) < new Date());
		const isMaxed = invite.max_uses !== null && invite.use_count >= invite.max_uses;
		return !isExpired && !isMaxed;
	}

	function copyInviteLink(invite: Invite) {
		const normalizedUrl = server.controlPlaneUrl.replace(/\/+$/, "");
		const link = `${normalizedUrl}/invite/${invite.token}/page`;
		navigator.clipboard.writeText(link);
		new Notice("Invite link copied!");
	}

	async function revokeInvite(inviteId: string) {
		if (!(await confirmDialog(live.app, "Revoke this invite link?"))) return;
		try {
			if (live.shareClientManager) {
				await live.shareClientManager.revokeInvite(share.serverId, share.id, inviteId);
			} else if (live.shareClient) {
				await live.shareClient.revokeInvite(share.id, inviteId);
			}
			new Notice("Invite revoked");
			invites = await loadInvites();
		} catch (e: unknown) {
			new Notice(`Failed to revoke invite: ${e instanceof Error ? e.message : "Unknown error"}`);
		}
	}

	// Visibility
	async function updateVisibility(newVisibility: string) {
		let password: string | undefined;
		if (newVisibility === "protected") {
			const input = await promptDialog(live.app, "Enter password for protected share:");
			if (!input) {
				new Notice("Password is required for protected shares");
				currentShare = { ...currentShare }; // trigger re-render to reset
				return;
			}
			password = input;
		}
		if (!(await confirmDialog(live.app, `Change visibility to ${newVisibility}?`))) {
			currentShare = { ...currentShare };
			return;
		}
		try {
			const payload: any = { visibility: newVisibility };
			if (password) payload.password = password;
			let updated;
			if (live.shareClientManager) {
				updated = await live.shareClientManager.updateShare(share.serverId, share.id, payload);
			} else if (live.shareClient) {
				updated = await live.shareClient.updateShare(share.id, payload);
			}
			if (updated) currentShare = { ...currentShare, ...updated };
			new Notice(`Visibility changed to ${newVisibility}`);
		} catch (e: unknown) {
			new Notice(`Failed: ${e instanceof Error ? e.message : "Unknown error"}`);
			currentShare = { ...currentShare };
		}
	}

	// Delete
	async function deleteShare() {
		if (!(await confirmDialog(live.app, `Delete "${currentShare.path}"? This cannot be undone.`))) return;
		try {
			if (live.shareClientManager) {
				await live.shareClientManager.deleteShare(share.serverId, share.id);
			} else if (live.shareClient) {
				await live.shareClient.deleteShare(share.id);
			}
			// Clean up local VaultShare
			const localFolder = live.shareRegistry.locate((sf) => sf.entityGuid === share.id);
			if (localFolder) {
				live.shareRegistry.delete(localFolder);
				live.explorerDecorations?.refreshExistingRows();
			}
			new Notice("Share deleted");
			dispatch("deleted");
		} catch (e: unknown) {
			new Notice(`Failed to delete: ${e instanceof Error ? e.message : "Unknown error"}`);
		}
	}

	// Web Publishing
	async function toggleWebPublishing(enabled: boolean) {
		if (enabled && currentShare.visibility === "private") {
			// Private shares need visibility change before web publishing
			const newVisibility = await choiceDialog(
				live.app,
				'This share is private. Web publishing requires "public" or "protected" visibility. Choose how you want to publish:',
				[
					{ label: "Make public (open access)", value: "public" },
					{ label: "Make protected (password)", value: "protected" },
				]
			);
			if (!newVisibility) {
				syncPublishCheckbox();
				return;
			}

			try {
				const payload = { visibility: newVisibility as "public" | "protected" };
				if (live.shareClientManager) {
					await live.shareClientManager.updateShare(share.serverId, share.id, payload);
				} else if (live.shareClient) {
					await live.shareClient.updateShare(share.id, payload);
				}
				currentShare = { ...currentShare, visibility: newVisibility as "public" | "protected" };
			} catch (e: unknown) {
				if (e instanceof VisibilityNotAllowedApiError) {
					const info = e.visibilityInfo;
					new Notice(
						`'${info.visibility}' visibility requires a higher plan. ` +
						`Your plan allows: ${info.allowed.join(", ")}. Upgrade to unlock.`,
						8000,
					);
				} else {
					console.error("Failed to change visibility:", e);
					new Notice("Failed to change visibility");
				}
				syncPublishCheckbox();
				return;
			}
		}

		try {
			const updatePayload: any = { web_published: enabled };
			if (enabled) {
				if (currentShare.kind === "doc") {
					const content = await getDocumentContent(currentShare.path);
					if (content) updatePayload.web_content = content;
				} else if (currentShare.kind === "folder") {
					const items = await getFolderItems(currentShare.path);
					if (items.length > 0) {
						await pushFolderContentToServer(currentShare.path, items);
						updatePayload.web_folder_items = items;
					}
				}
			}

			let updated;
			if (live.shareClientManager) {
				updated = await live.shareClientManager.updateShare(share.serverId, share.id, updatePayload);
			} else if (live.shareClient) {
				updated = await live.shareClient.updateShare(share.id, updatePayload);
			}
			if (updated) {
				currentShare = { ...currentShare, ...updated };
				editingSlug = currentShare.web_slug || "";
			}
			new Notice(enabled ? "Published to web!" : "Unpublished from web");
		} catch (e: unknown) {
			if (e instanceof LimitExceededApiError) {
				const info = e.limitInfo;
				new Notice(
					`Web publish limit reached (${info.current}/${info.max} on ${info.plan} plan). ` +
					`Upgrade your plan to publish more.`,
					8000,
				);
			} else if (e instanceof VisibilityNotAllowedApiError) {
				const info = e.visibilityInfo;
				new Notice(
					`'${info.visibility}' visibility requires a higher plan. ` +
					`Your plan allows: ${info.allowed.join(", ")}. Upgrade to unlock.`,
					8000,
				);
			} else {
				new Notice(`Failed: ${e instanceof Error ? e.message : "Unknown error"}`);
			}
			syncPublishCheckbox();
		}
	}

	// TR-25-followup (#1d244fb4): this "sync now" action pushes content
	// directly, bypassing WebSyncManager's own syncFile()/syncFolderFile() —
	// echo-guard each push the same way (guard is ref-counted, safe per-call).
	async function syncWebContent() {
		if (currentShare.kind === "doc") {
			try {
				const content = await getDocumentContent(currentShare.path);
				if (!content) { new Notice("Could not read document"); return; }
				let updated;
				if (live.shareClientManager) {
					updated = await withOutboundSyncGuard(live.webSyncManager, () =>
						live.shareClientManager!.updateShare(share.serverId, share.id, { web_content: content })
					);
				} else if (live.shareClient) {
					updated = await withOutboundSyncGuard(live.webSyncManager, () =>
						live.shareClient!.updateShare(share.id, { web_content: content })
					);
				}
				if (updated) currentShare = { ...currentShare, ...updated };
				new Notice("Content synced!");
			} catch (e: unknown) {
				new Notice(`Failed to sync: ${e instanceof Error ? e.message : "Unknown error"}`);
			}
		} else if (currentShare.kind === "folder") {
			try {
				const items = await getFolderItems(currentShare.path);
				if (items.length === 0) { new Notice("Folder empty"); return; }
				let updated;
				if (live.shareClientManager) {
					updated = await withOutboundSyncGuard(live.webSyncManager, () =>
						live.shareClientManager!.updateShare(share.serverId, share.id, { web_folder_items: items })
					);
				} else if (live.shareClient) {
					updated = await withOutboundSyncGuard(live.webSyncManager, () =>
						live.shareClient!.updateShare(share.id, { web_folder_items: items })
					);
				}
				if (updated) currentShare = { ...currentShare, ...updated };

				// Sync file content
				const slug = currentShare.web_slug;
				if (slug) {
					let synced = 0;
					for (const item of items) {
						if (item.type === "doc") {
							try {
								const content = await getDocumentContent(`${currentShare.path}/${item.path}`);
								if (content) {
									if (live.shareClientManager) {
										const clientManager = live.shareClientManager;
										await withOutboundSyncGuard(live.webSyncManager, () =>
											clientManager.syncFolderFileContent(share.serverId, slug, item.path, content)
										);
									} else if (live.shareClient) {
										const client = live.shareClient;
										await withOutboundSyncGuard(live.webSyncManager, () =>
											client.syncFolderFileContent(slug, item.path, content)
										);
									}
									synced++;
								}
							} catch { /* skip individual file errors */ }
						}
					}
					new Notice(`Synced ${synced} files`);
				} else {
					new Notice(`Folder synced: ${items.length} items`);
				}
			} catch (e: unknown) {
				new Notice(`Failed to sync: ${e instanceof Error ? e.message : "Unknown error"}`);
			}
		}
	}

	async function updateWebNoindex(noindex: boolean) {
		try {
			let updated;
			if (live.shareClientManager) {
				updated = await live.shareClientManager.updateShare(share.serverId, share.id, { web_noindex: noindex });
			} else if (live.shareClient) {
				updated = await live.shareClient.updateShare(share.id, { web_noindex: noindex });
			}
			if (updated) currentShare = { ...currentShare, ...updated };
			new Notice(noindex ? "Indexing disabled" : "Indexing enabled");
		} catch (e: unknown) {
			new Notice(`Failed: ${e instanceof Error ? e.message : "Unknown error"}`);
		}
	}

	// See handleMemberRoleChange above -- same reason for the wrapper.
	function handleSyncModeChange(value: string) {
		updateSyncMode(value as "auto" | "manual");
	}

	async function updateSyncMode(mode: "auto" | "manual") {
		try {
			let updated;
			if (live.shareClientManager) {
				updated = await live.shareClientManager.updateShare(share.serverId, share.id, { web_sync_mode: mode });
			} else if (live.shareClient) {
				updated = await live.shareClient.updateShare(share.id, { web_sync_mode: mode });
			}
			if (updated) currentShare = { ...currentShare, ...updated };
			if (live.webSyncManager) {
				if (mode === "auto") {
					live.webSyncManager.registerAutoSyncShare(
						currentShare.path, currentShare.id, currentShare.serverId,
						currentShare.kind, currentShare.web_slug ?? undefined,
					);
					new Notice("Auto-sync enabled");
				} else {
					live.webSyncManager.unregisterAutoSyncShare(currentShare.path);
					new Notice("Auto-sync disabled");
				}
			} else {
				new Notice(`Sync mode: ${mode}`);
			}
		} catch (e: unknown) {
			new Notice(`Failed: ${e instanceof Error ? e.message : "Unknown error"}`);
		}
	}

	async function saveWebSlug() {
		const newSlug = editingSlug.trim().toLowerCase().replace(/[^a-z0-9-]/g, "-");
		if (!newSlug || newSlug === currentShare.web_slug) return;
		try {
			let updated;
			if (live.shareClientManager) {
				updated = await live.shareClientManager.updateShare(share.serverId, share.id, { web_slug: newSlug });
			} else if (live.shareClient) {
				updated = await live.shareClient.updateShare(share.id, { web_slug: newSlug });
			}
			if (updated) {
				currentShare = { ...currentShare, ...updated };
				editingSlug = currentShare.web_slug || "";
			}
			new Notice(`Slug updated: ${newSlug}`);
		} catch (e: unknown) {
			new Notice(`Failed: ${e instanceof Error ? e.message : "Unknown error"}`);
		}
	}

	// Helpers
	async function getDocumentContent(path: string): Promise<string | null> {
		try {
			const file = live.app.vault.getAbstractFileByPath(path);
			if (file && "extension" in file) return await live.app.vault.read(file as any);
			return null;
		} catch { return null; }
	}

	async function getFolderItems(folderPath: string): Promise<WebFolderEntry[]> {
		try {
			const folder = live.app.vault.getAbstractFileByPath(folderPath);
			if (!folder || !(folder instanceof TFolder)) return [];
			const items: WebFolderEntry[] = [];
			const process = (f: TFolder) => {
				for (const child of f.children) {
					const rel = child.path.substring(folderPath.length + 1);
					if (child instanceof TFile) {
						if (child.extension === "canvas") {
							items.push({ path: rel, name: child.basename, type: "canvas" });
						} else if (child.extension === "md") {
							items.push({ path: rel, name: child.basename, type: "doc" });
						}
					} else if (child instanceof TFolder) {
						items.push({ path: rel, name: child.name, type: "folder" });
						process(child);
					}
				}
			};
			process(folder);
			return items;
		} catch { return []; }
	}

	// The server only counts a folder share as publishable once at least one
	// item's `content`/`storage_key` is populated (share_service.
	// _share_has_publishable_content) -- and the ONLY endpoint that populates
	// either is the per-file conditional sync-write protocol, keyed by
	// share id so it works before the share has ever been published (unlike
	// syncFolderFileContent below, which needs an existing web_slug and so
	// can only ever run AFTER a first successful publish). Without this,
	// toggling "Publish to Web" on a folder share 400s forever regardless of
	// how much real local content exists, because the generic
	// UpdateShareRequest.web_folder_items the toggle sends is structure-only
	// (path/name/type) by design (#d425920b).
	async function pushFolderContentToServer(folderPath: string, items: WebFolderEntry[]): Promise<void> {
		const syncable = items.filter((i) => i.type === "doc" || i.type === "canvas");
		if (syncable.length === 0) return;

		let indexed = new Map<string, string>();
		try {
			const index = live.shareClientManager
				? await live.shareClientManager.getFilesIndex(share.serverId, share.id)
				: await live.shareClient!.getFilesIndex(share.id);
			indexed = new Map(index.map((i) => [i.path, i.sha256]));
		} catch {
			// No prior index (fresh share, or the endpoint genuinely has
			// nothing yet) -- treat every item as never-before-synced below.
		}

		for (const item of syncable) {
			const content = await getDocumentContent(`${folderPath}/${item.path}`);
			if (content === null) continue; // file vanished between listing and read -- skip, not fatal
			const localSha = await sha256Hex(new TextEncoder().encode(content).buffer as ArrayBuffer);
			const remoteSha = indexed.get(item.path);
			if (remoteSha === localSha) continue; // already in sync, don't churn a needless write

			const precondition = remoteSha ? { ifMatchSha256: remoteSha } : ({ create: true } as const);
			const mime = item.type === "canvas" ? "application/json" : "text/markdown; charset=utf-8";
			if (live.shareClientManager) {
				await live.shareClientManager.syncWriteFile(share.serverId, share.id, item.path, content, precondition, mime);
			} else if (live.shareClient) {
				await live.shareClient.syncWriteFile(share.id, item.path, content, precondition, mime);
			}
		}
	}

	$: activeInvites = invites.filter(i => !i.revoked_at);
	$: isPublished = currentShare.web_published ?? false;
	$: syncMode = currentShare.web_sync_mode ?? "manual";
	$: noindex = currentShare.web_noindex ?? true;

	// Local folder connection
	let isConnectedLocally = false;
	let localFolderPath = "";

	function checkLocalConnection() {
		const localFolder = live.shareRegistry.locate((sf) => sf.entityGuid === share.id);
		isConnectedLocally = !!localFolder;
		localFolderPath = localFolder ? localFolder.path : "";
	}

	// Check on mount and whenever loading finishes
	$: if (!loading) checkLocalConnection();

	function connectToFolder() {
		const modal = new FolderPathPickerModal(
			live.app,
			"Choose local folder for this share...",
			new Set(),
			live.shareRegistry,
			async (folderPath: string) => {
				try {
					const vaultShare = live.shareRegistry.new(folderPath, share.id, "relay-onprem", true);
					if (vaultShare) {
						await vaultShare.setOnpremServerId(share.serverId);
						// onpremServerId is set AFTER construction, so the constructor's
						// own auto-connect gate never saw it — connect explicitly now
						// that the server is known (#ea8389cf).
						void vaultShare.bringOnline();
					}
					live.explorerDecorations?.refreshExistingRows();
					new Notice("Folder connected! Syncing...");
					checkLocalConnection();
				} catch (e: unknown) {
					new Notice(`Failed to connect folder: ${e instanceof Error ? e.message : "Unknown error"}`);
				}
			},
		);
		modal.open();
	}

	async function disconnectFolder() {
		if (!(await confirmDialog(live.app, `Disconnect local folder "${localFolderPath}" from this share? Local files will not be deleted.`))) return;
		const localFolder = live.shareRegistry.locate((sf) => sf.entityGuid === share.id);
		if (localFolder) {
			live.shareRegistry.delete(localFolder);
			live.explorerDecorations?.refreshExistingRows();
			new Notice("Folder disconnected");
			checkLocalConnection();
		}
	}
</script>

<div class="evc-share-detail">
	{#if loading}
		<div class="evc-loading">Loading share details...</div>
	{:else}
		<!-- Share Info -->
		<div class="evc-detail-header">
			<h3 class="evc-detail-title">{currentShare.path}</h3>
			<div class="evc-detail-badges">
				<span class="evc-badge">{currentShare.kind}</span>
				<span class="evc-badge evc-badge-{currentShare.visibility}">{currentShare.visibility}</span>
				<span class="evc-detail-date">{new Date(currentShare.created_at).toLocaleDateString()}</span>
				<button class="evc-link-btn" on:click={copyId}>Copy ID</button>
			</div>
		</div>

		<!-- Local Folder Connection (folder shares only) -->
		{#if currentShare.kind === "folder"}
			<div class="evc-section">
				<div class="evc-section-title">Local Folder</div>
				{#if isConnectedLocally}
					<div class="evc-connection-row">
						<div class="evc-connection-info">
							<span class="evc-connection-path">{localFolderPath}</span>
							<span class="evc-connection-status">Connected and syncing</span>
						</div>
						<button class="evc-btn-danger evc-small-btn" on:click={disconnectFolder}>Disconnect</button>
					</div>
				{:else}
					<div class="evc-connection-row">
						<div class="evc-connection-info">
							<span class="evc-connection-status">Not connected to a local folder</span>
						</div>
						<button class="mod-cta" on:click={connectToFolder}>Connect to local folder</button>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Members -->
		<div class="evc-section">
			<div class="evc-section-title">Members</div>
			{#if members.length === 0}
				<div class="evc-empty-inline">No members yet.</div>
			{:else}
				<div class="evc-member-list">
					{#each members as member (member.id)}
						<div class="evc-member-item">
							<div class="evc-member-info">
								<span class="evc-member-email">{member.user_email}</span>
								{#if !isOwner}
									<span class="evc-badge">{member.role}</span>
								{/if}
							</div>
							{#if isOwner}
								<div class="evc-member-actions">
									<select
										class="dropdown evc-role-select"
										value={member.role}
										on:change={(e) => handleMemberRoleChange(member.user_id, e.currentTarget.value)}
									>
										<option value="viewer">Viewer</option>
										<option value="editor">Editor</option>
									</select>
									<button class="evc-btn-danger" on:click={() => removeMember(member.user_id)}>Remove</button>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			{#if isOwner}
				<div class="evc-add-member">
					<input
						type="text"
						placeholder="user@example.com"
						bind:value={newMemberEmail}
						on:keypress={(e) => { if (e.key === 'Enter') addMember(); }}
					/>
					<select class="dropdown evc-role-select" bind:value={newMemberRole}>
						<option value="viewer">Viewer</option>
						<option value="editor">Editor</option>
					</select>
					<button class="mod-cta" on:click={addMember}>Add</button>
				</div>
			{/if}
		</div>

		<!-- Invites (owner only) -->
		{#if isOwner}
			<div class="evc-section">
				<div class="evc-section-header">
					<div class="evc-section-title">Invite Links</div>
					<button class="evc-small-btn" on:click={() => dispatch('createInvite')}>Create Invite</button>
				</div>
				{#if activeInvites.length === 0}
					<div class="evc-empty-inline">No active invite links.</div>
				{:else}
					<div class="evc-invite-list">
						{#each activeInvites as invite (invite.id)}
							<div class="evc-invite-item" class:evc-invite-invalid={!isInviteValid(invite)}>
								<div class="evc-invite-info">
									<span class="evc-invite-role">{invite.role} invite</span>
									<span class="evc-invite-desc">{getInviteDescription(invite)}</span>
								</div>
								<div class="evc-invite-actions">
									<button class="evc-small-btn" on:click={() => copyInviteLink(invite)}>Copy Link</button>
									<button class="evc-btn-danger evc-small-btn" on:click={() => revokeInvite(invite.id)}>Revoke</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Agent Keys (owner only) -->
		{#if isOwner}
		<div class="evc-section">
			<div class="evc-section-header">
				<div class="evc-section-title">Agent Keys</div>
				<button class="evc-small-btn" on:click={() => dispatch('agentKeys')}>Manage</button>
			</div>
			<div class="evc-setting-desc">
				API keys for automated agents to access this share without your login credentials.
			</div>
		</div>
		{/if}

		<!-- Web Publishing (owner + server supports it) -->
		{#if isOwner && webPublishEnabled}
			<div class="evc-section">
				<div class="evc-section-title">Web Publishing</div>

				<div class="evc-setting-row">
					<div class="evc-setting-info">
						<span>Publish to Web</span>
					</div>
					<label class="checkbox-container" class:is-enabled={isPublished}>
						<input type="checkbox" checked={isPublished} bind:this={publishCheckboxEl} on:change={(e) => toggleWebPublishing(e.currentTarget.checked)} />
					</label>
				</div>

				{#if isPublished}
					{#if currentShare.web_url}
						<div class="evc-setting-row">
							<div class="evc-setting-info">
								<span>Web URL</span>
								<span class="evc-setting-desc">{currentShare.web_url}</span>
							</div>
							<div class="evc-setting-actions">
								<button class="evc-small-btn" on:click={() => { navigator.clipboard.writeText(currentShare.web_url || ''); new Notice('URL copied!'); }}>Copy</button>
								<button class="evc-small-btn" on:click={() => window.open(currentShare.web_url || '', '_blank')}>Open</button>
							</div>
						</div>
					{/if}

					<div class="evc-setting-row">
						<div class="evc-setting-info">
							<span>Sync Content</span>
						</div>
						<button class="mod-cta evc-small-btn" on:click={syncWebContent}>Sync Now</button>
					</div>

					<div class="evc-setting-row">
						<div class="evc-setting-info">
							<span>Allow search engines</span>
						</div>
						<label class="checkbox-container" class:is-enabled={!noindex}>
							<input type="checkbox" checked={!noindex} on:change={(e) => updateWebNoindex(!e.currentTarget.checked)} />
						</label>
					</div>

					<div class="evc-setting-row">
						<div class="evc-setting-info">
							<span>Sync Mode</span>
						</div>
						<select class="dropdown" value={syncMode} on:change={(e) => handleSyncModeChange(e.currentTarget.value)}>
							<option value="manual">Manual</option>
							<option value="auto">Auto</option>
						</select>
					</div>

					{#if currentShare.web_slug}
						<div class="evc-setting-row">
							<div class="evc-setting-info">
								<span>Web Slug</span>
							</div>
							<div class="evc-slug-edit">
								<input type="text" bind:value={editingSlug} placeholder="my-document" />
								<button class="evc-small-btn" on:click={saveWebSlug}>Save</button>
							</div>
						</div>
					{/if}
				{/if}
			</div>
		{/if}

		<!-- Actions (owner only) -->
		{#if isOwner}
			<div class="evc-section">
				<div class="evc-section-title">Actions</div>

				<div class="evc-setting-row">
					<div class="evc-setting-info">
						<span>Change Visibility</span>
						<span class="evc-setting-desc">Control who can access this share</span>
					</div>
					<select
						class="dropdown"
						value={currentShare.visibility}
						on:change={(e) => updateVisibility(e.currentTarget.value)}
					>
						<option value="private">Private</option>
						<option value="public">Public</option>
						<option value="protected">Protected</option>
					</select>
				</div>

				<div class="evc-setting-row">
					<div class="evc-setting-info">
						<span>Delete Share</span>
						<span class="evc-setting-desc">Permanently delete this share</span>
					</div>
					<button class="evc-btn-danger" on:click={deleteShare}>Delete</button>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.evc-share-detail {
		display: flex;
		flex-direction: column;
		gap: 20px;
	}

	.evc-loading {
		padding: 24px;
		text-align: center;
		color: var(--text-muted);
	}

	.evc-detail-header {
		padding-bottom: 12px;
		border-bottom: 1px solid var(--background-modifier-border);
	}

	.evc-detail-title {
		margin: 0 0 8px 0;
		padding: 0;
		font-size: 1.2em;
	}

	.evc-detail-badges {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
		font-size: 0.85em;
	}

	.evc-detail-date {
		color: var(--text-faint);
	}

	.evc-link-btn {
		font-size: 0.75em;
		font-weight: 500;
		padding: 2px 8px;
		cursor: pointer;
		background: var(--background-modifier-border);
		border-radius: 4px;
		color: var(--text-muted);
		border: none;
		line-height: inherit;
	}

	.evc-link-btn:hover {
		background: var(--background-modifier-hover);
		color: var(--text-normal);
	}

	.evc-section {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.evc-section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.evc-section-title {
		font-weight: 600;
		font-size: 1em;
	}

	.evc-empty-inline {
		color: var(--text-muted);
		font-size: 0.9em;
		padding: 8px 0;
	}

	.evc-badge {
		font-size: 0.75em;
		padding: 2px 8px;
		border-radius: 4px;
		font-weight: 500;
		background: var(--background-modifier-border);
		color: var(--text-muted);
	}

	.evc-badge-public {
		background: hsla(120, 40%, 50%, 0.15);
		color: var(--text-success, #22863a);
	}

	.evc-badge-private {
		background: var(--background-modifier-border);
	}

	.evc-badge-protected {
		background: hsla(45, 80%, 50%, 0.15);
		color: var(--text-warning, #b08800);
	}

	/* Local Folder Connection */
	.evc-connection-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 12px;
		background: var(--background-secondary);
		border-radius: 6px;
		gap: 12px;
	}

	.evc-connection-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.evc-connection-path {
		font-weight: 500;
		word-break: break-all;
	}

	.evc-connection-status {
		font-size: 0.85em;
		color: var(--text-muted);
	}

	/* Members */
	.evc-member-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.evc-member-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8px 12px;
		background: var(--background-secondary);
		border-radius: 6px;
	}

	.evc-member-info {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.evc-member-email {
		font-weight: 500;
	}

	.evc-member-actions {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.evc-role-select {
		font-size: 0.85em;
		padding: 2px 24px 2px 6px;
		min-width: 80px;
	}

	.evc-add-member {
		display: flex;
		gap: 6px;
		align-items: center;
		margin-top: 4px;
	}

	.evc-add-member input {
		flex: 1;
	}

	/* Invites */
	.evc-invite-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.evc-invite-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8px 12px;
		background: var(--background-secondary);
		border-radius: 6px;
	}

	.evc-invite-invalid {
		opacity: 0.6;
	}

	.evc-invite-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.evc-invite-role {
		font-weight: 500;
		font-size: 0.9em;
	}

	.evc-invite-desc {
		font-size: 0.8em;
		color: var(--text-muted);
	}

	.evc-invite-actions {
		display: flex;
		gap: 6px;
	}

	/* Settings rows */
	.evc-setting-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8px 0;
		border-bottom: 1px solid var(--background-modifier-border);
		gap: 12px;
	}

	.evc-setting-row:last-child {
		border-bottom: none;
	}

	.evc-setting-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1;
	}

	.evc-setting-desc {
		font-size: 0.85em;
		color: var(--text-muted);
	}

	.evc-setting-actions {
		display: flex;
		gap: 6px;
	}

	.evc-slug-edit {
		display: flex;
		gap: 6px;
		align-items: center;
	}

	.evc-slug-edit input {
		width: 160px;
	}

	/* Buttons */
	.evc-small-btn {
		font-size: 0.85em;
		padding: 4px 10px;
	}

	.evc-btn-danger {
		color: var(--text-error);
		border-color: var(--text-error);
	}

	.evc-btn-danger:hover {
		background: var(--text-error);
		color: var(--text-on-accent);
	}
</style>
