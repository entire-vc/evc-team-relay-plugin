<script lang="ts">
	import {
		ChevronRight,
		Folder as FolderIcon,
		FolderLock,
		Home as HomeIcon,
		Layers,
		Satellite as SatelliteIcon,
	} from "lucide-svelte";
	import type { RelayWorkspace, RemoteFolderRecord } from "src/RelayModel";
	import type { VaultShare } from "src/VaultShare";

	// A shared base carries the one field every breadcrumb kind has in
	// common, so each concrete variant only spells out what makes it
	// different (its discriminant + payload).
	interface BreadcrumbBase {
		onClick?: () => void;
	}

	interface HomeWaypoint extends BreadcrumbBase {
		type: "home";
	}

	interface TextWaypoint extends BreadcrumbBase {
		type: "text";
		text: string;
	}

	interface RelayWaypoint extends BreadcrumbBase {
		type: "relay";
		relay: RelayWorkspace;
	}

	interface FolderWaypoint extends BreadcrumbBase {
		type: "folder";
		folder: VaultShare;
	}

	interface RemoteFolderWaypoint extends BreadcrumbBase {
		type: "remoteFolder";
		remoteFolder: RemoteFolderRecord;
	}

	type NavWaypoint =
		| HomeWaypoint
		| TextWaypoint
		| RelayWaypoint
		| FolderWaypoint
		| RemoteFolderWaypoint;

	export let waypoints: NavWaypoint[];
	export let tagName = "h4";

	function activate(item: NavWaypoint): void {
		item.onClick?.();
	}

	function handleKeypress(item: NavWaypoint, e: KeyboardEvent): void {
		if (e.key === "Enter" || e.key === " ") activate(item);
	}

	function iconFor(item: NavWaypoint) {
		switch (item.type) {
			case "home":
				return HomeIcon;
			case "relay":
				return SatelliteIcon;
			case "folder":
				return Layers;
			case "remoteFolder":
				return item.remoteFolder?.isPrivate ? FolderLock : FolderIcon;
			default:
				return null;
		}
	}

	// Each rule is independent (not mutually exclusive): a single-item list
	// gets both "first-item" and "evc-last-item" on that one element, matching
	// the upstream template's three separate ternaries.
	function positionClasses(index: number, total: number): string {
		const classes: string[] = [];
		if (index === 0) classes.push("first-item");
		if (index === total - 1) classes.push("evc-last-item");
		if (index > 0 && index < total - 1) classes.push("middle-item");
		return classes.join(" ");
	}
</script>

<svelte:element this={tagName} class="evc-breadcrumb-container">
	{#each waypoints as item, index}
		{#if index > 0}
			<ChevronRight size={16} class="evc-breadcrumb-separator" />
		{/if}

		<span class="evc-breadcrumb-item-wrapper">
			<span
				on:click={() => activate(item)}
				on:keypress={(e) => handleKeypress(item, e)}
				tabindex="0"
				role="button"
				class="evc-breadcrumb-item {positionClasses(index, waypoints.length)}"
			>
				{#if iconFor(item)}
					<svelte:component this={iconFor(item)} class="svg-icon evc-breadcrumb-icon" />
				{/if}
				<span class="evc-breadcrumb-text">
					{#if item.type === "folder"}
						{item.folder.folderLabel}
					{:else if item.type === "remoteFolder"}
						{#if item.remoteFolder.folderName}
							{item.remoteFolder.folderName}
						{:else}
							<span class="faint">(Untitled folder)</span>
						{/if}
					{:else if item.type === "relay"}
						{#if item.relay.displayName}
							{item.relay.displayName}
						{:else}
							<span class="faint">(Untitled Relay Server)</span>
						{/if}
					{:else if item.type === "text"}
						{item.text}
					{/if}
				</span>
			</span>
		</span>
	{/each}
</svelte:element>

<style>
	@media (max-width: 768px) {
		.middle-item .evc-breadcrumb-text {
			display: none;
		}

		.evc-breadcrumb-item-wrapper:last-child {
			flex: 1;
			min-width: 0;
			overflow: hidden;
		}

		.evc-last-item,
		.evc-last-item .evc-breadcrumb-text {
			overflow: hidden;
		}

		.evc-last-item .evc-breadcrumb-text {
			text-overflow: ellipsis;
			white-space: nowrap;
		}
	}

	.evc-breadcrumb-text {
		display: inline-block;
	}

	.evc-breadcrumb-item {
		align-items: center;
		cursor: pointer;
		display: flex;
		gap: 0.3em;
		min-width: 0;
	}

	.evc-breadcrumb-item-wrapper {
		align-items: center;
		display: flex;
		gap: 0.3em;
		min-width: 0;
	}

	.evc-breadcrumb-container {
		align-items: center;
		display: flex;
		gap: 8px;
		overflow: hidden;
	}

	.faint {
		color: var(--text-faint);
	}
</style>
