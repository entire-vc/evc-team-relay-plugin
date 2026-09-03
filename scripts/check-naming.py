#!/usr/bin/env python3
"""Gate 4: NAMES shared with upstream — files, directories, types, members.

Why a fourth gate. Gates 1-3 all read the CONTENTS of lines: similarity score,
longest verbatim run, distinguishable retained lines. None of them looks at what
a thing is CALLED. A file can pass all three and still be `RelayManager.ts`
holding `class RelayManager` with `subscribe()`/`buildRelayRoles()` inside — and
anyone who opens the tree sees upstream's map before reading a single line. The
condition we are answering ("no longer a fork in substance") is judged on exactly
that first impression, without a diff.

What it compares, against upstream pinned at the fork point:
  file    — a source file at the same relative path in both trees
  dir     — a directory at the same relative path in both trees
  type    — a class / interface / type-alias / enum name declared in BOTH trees
  member  — Class.member where both trees declare that class AND that member
  export  — an exported function / const / let name declared in BOTH trees

DECLARED, not used. `TFile` appears in both trees hundreds of times and is
Obsidian's name; nobody declares it, so it never enters the count. This is the
distinction that keeps the gate pointed at our own naming.

The member axis ALSO compares a renamed class against its upstream
PREDECESSOR (PREDECESSOR_TYPES below), not just against a same-named class
-- required because "both trees declare that class" (line above) is
impossible for a class we renamed, which silently removed its entire member
set from the ordinary comparison for as long as this gate existed (Mesh
#a2f4027a). Renaming `RelayManager` to `RelayRegistry` does not, on its own,
rename `subscribe()`/`buildRelayRoles()` inside it.

Four baskets, per the epic convention (Mesh #f3eb7b30):
  contract    — a name we do not get to choose: the Obsidian plugin interface,
                Svelte/DOM component API, the wire/DB field names kept
                deliberately for compatibility, and vendored third-party files.
                Enumerated BY NAME below with a reason, never by directory
                prefix — a prefix silently annexes whatever is added under it
                later.
  convergent  — an independent author writing this from scratch lands on the
                same word, on stated evidence (a corpus count or the same
                platform declaring the same concept). Type/export axis only.
  adjudicated — a name we ARE free to rename, named and reasoned here (gate
                3's ADJUDICATED convention, applied to the member axis; Mesh
                #4a73e623), because renaming it THIS WAVE costs more than the
                wave's own board buys. Not permanent: a future wave deletes
                the entry and does the rename.
  work        — everything else. This is the number that must reach zero
                (modulo the adjudicated exceptions named above).

Usage:
  check-naming.py <upstream_src> <our_src> [--max-work N] [--show-samples FILE]
                  [--json out.json] [--limit N]
Exit 1 if the work basket exceeds --max-work (default: report only, exit 0).
Exit 2 if the probe could not run — never reports clean when it failed to look.
"""
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# Imported, not re-typed. check-verbatim-distinct.py (gate 3) says so in its own
# comment: two hand-copies of one basket list drift apart silently, and we have
# already paid for that once on this epic (Mesh #6b88fc6f point 5). If that file
# moves, this gate fails loudly rather than falling back to an empty set.
def _load_gate3():
    path = os.path.join(HERE, 'check-verbatim-distinct.py')
    spec = importlib.util.spec_from_file_location('gate3', path)
    if spec is None or spec.loader is None:
        print(f"FATAL: cannot load basket lists from {path}", file=sys.stderr)
        sys.exit(2)
    mod = importlib.util.module_from_spec(spec)
    # Importing gate 3 would otherwise drop scripts/__pycache__/ into the repo
    # on every run, so a measurement leaves the working tree dirty. A probe
    # should not modify what it measures.
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:                                  # noqa: BLE001
        print(f"FATAL: cannot load basket lists from {path}: {exc}",
              file=sys.stderr)
        sys.exit(2)
    finally:
        sys.dont_write_bytecode = prev
    if not getattr(mod, 'VENDOR_FILES', None):
        print(f"FATAL: {path} no longer defines VENDOR_FILES", file=sys.stderr)
        sys.exit(2)
    return mod


_G3 = _load_gate3()
VENDOR_FILES = _G3.VENDOR_FILES

# Directories that ARE the vendored third-party code the VENDOR_FILES entries
# live in. Kept as a separate, explicitly-listed set because the dir axis has no
# per-file entry to match against. Each carries its own upstream LICENSE.
VENDOR_DIRS = frozenset({
    'y-codemirror.next',   # Kevin Jahns, y-codemirror.next
    'client',              # y-websocket-derived provider
    'storage',             # y-indexeddb
})
# 'pocketbase' left this set on 2026-08-23 (Mesh #84bd2a91): the directory is
# gone from src/ entirely, so excusing its name excused nothing.

# ---------------------------------------------------------------------------
# CONTRACT basket. Every entry is a name we are not free to change, with the
# authority that fixes it. Anything not listed here is work, including names
# that merely feel unavoidable.
# ---------------------------------------------------------------------------

# Obsidian plugin API: methods Obsidian itself calls on our objects. Renaming
# any of these does not rename anything — it deletes the hook.
# Source: obsidian.d.ts in the pinned obsidian dependency.
OBSIDIAN_HOOKS = frozenset({
    # Plugin
    'onload', 'onunload', 'onExternalSettingsChange', 'onUserEnable',
    'onLayoutReady', 'registerEvent', 'registerDomEvent', 'registerInterval',
    'addChild', 'removeChild', 'loadData', 'saveData',
    # ItemView / View / FileView
    'getViewType', 'getDisplayText', 'getIcon', 'onOpen', 'onClose',
    'onPaneMenu', 'getState', 'setState', 'getEphemeralState',
    'setEphemeralState', 'canAcceptExtension', 'getViewData', 'setViewData',
    'onLoadFile', 'onUnloadFile',
    # Modal / PluginSettingTab
    'display', 'hide',
    # SuggestModal / FuzzySuggestModal / EditorSuggest
    'getSuggestions', 'renderSuggestion', 'selectSuggestion', 'getItems',
    'getItemText', 'onChooseItem', 'onChooseSuggestion', 'onNoSuggestion',
    'onTrigger',
    # NOT here, though the first draft had them: `load`, `unload`, `register`,
    # `clear`, `update`, `destroy`, `onChange`, `onKeydown`, `onSubmit`,
    # `onRename`, `onDelete`. Each exists somewhere in obsidian.d.ts, but each
    # is also an ordinary English verb we put on ~60 classes of our own that
    # extend nothing from Obsidian -- `SharedFolders.load`, `TokenStore.clear`,
    # `Destroyable.destroy`. Listing them globally excused those for free. A
    # genuine override of one will surface here as a single `work` row and can
    # be argued on its own; that is much cheaper than a silently green gate.
})

# Names the language or a framework calls by that exact name. Deliberately
# short. The first draft of this set also held `connect`, `disconnect`, `start`,
# `stop`, `send`, `close`, `open`, `destroy`, `dispose` and the `onmessage`
# family — none of which anything mandates on a class of ours. They were excusing
# ~90 shared members that we are perfectly free to rename, which is how a gate
# quietly becomes green without the code changing. When unsure, a name belongs in
# `work`: the cost of a wrong `work` entry is one argument, the cost of a wrong
# `contract` entry is a name nobody ever looks at again. Measured while drafting
# this file: the two tightening passes (scoping wire fields to their declaring
# files, then dropping the generic verbs) moved 211 names out of contract and
# into work -- 606 -> 466 -> 395. A basket assembled from names that merely FEEL
# unavoidable is off by more than a third.
# Names the LANGUAGE mandates. These need no scoping: `constructor` is
# `constructor` on any class in any file.
LANG_PROTOCOLS = frozenset({
    'constructor', 'toString', 'toJSON', 'valueOf', 'then', 'catch',
    'finally', 'next',
})

# The Svelte store contract is `subscribe(run) -> unsubscriber`. The RUN
# CALLBACK is the contract, so a zero-argument `subscribe()` is not it -- it is
# an ordinary method that happens to share the spelling. Measured: RelayManager
# declares `subscribe() {`, called as `this.relayManager.subscribe();` with no
# arguments, on a class extending HasLogging; it starts a PocketBase realtime
# subscription and we are entirely free to rename it. It sat in the contract
# basket until this check existed.
SVELTE_STORE_MEMBERS = frozenset({'subscribe'})

# Svelte's component lifecycle functions are IMPORTED and called at component
# top level, not declared as class members. Contract only inside a .svelte file.
SVELTE_LIFECYCLE = frozenset({
    'onMount', 'onDestroy', 'beforeUpdate', 'afterUpdate', 'tick',
})

# CodeMirror 6 mandates `update(ViewUpdate)` and `destroy()` on a PluginValue,
# by those exact names. Scoped to classes that ARE plugin values -- the naming
# convention upstream and we both follow -- rather than granted globally, which
# is what let ~60 unrelated `destroy`s into the contract basket on first draft.
CM_PLUGIN_MEMBERS = frozenset({'update', 'destroy'})

# Structural mirrors of an EXTERNAL API that ships no type declarations. Their
# MEMBER names are fixed by the real runtime object we cast onto -- Obsidian's
# built-in Canvas plugin, reached at LiveViews.ts:81 via
# `leaf.view as unknown as CanvasView`. Rename a member and the mirror silently
# stops describing the object every caller goes through; the compiler cannot
# catch it, because the cast erases the check. src/CanvasView.ts says as much in
# its own header comment.
#
# These interfaces `extends` nothing, so the nominal base-class resolver below
# cannot see them -- structural typing has no chain to walk. Hence a by-name
# enumeration, which is the same instrument the rest of this file uses.
#
# NB: only the MEMBERS are contract. The interface NAMES (`CanvasView` itself)
# are ours -- nothing external requires that spelling -- so they stay in work.
# UPDATED (Mesh #a2f4027a): `CanvasView`/`CanvasNode`/`CanvasEdge` were
# themselves renamed to `HostCanvasView`/`HostCanvasNode`/`HostCanvasEdge` in a
# later wave -- this set held the OLD names, so it silently stopped matching
# anything (`cls in STRUCTURAL_EXTERNAL_TYPES` fails for `HostCanvasView`,
# which nobody would notice since a failing membership check on a dead entry
# does not raise, it just quietly excuses zero members instead of the
# intended ones). `CanvasItem` has no successor found (either genuinely
# removed or below this task's detection floor) -- left as-is, harmless if
# still dead. `CanvasNodeData`/`CanvasEdgeData`/`CanvasData` were NOT renamed
# (by design -- see CONVERGENT_TYPES's platform test) and are correctly still
# their original names.
# UPDATED (W16, Mesh #2e075374): `HostCanvas` itself (predecessor `Canvas` ->
# `ObsidianCanvas` -> `HostCanvas`, per PREDECESSOR_TYPES) was MISSING from
# this set entirely -- not a stale entry like the four above, just never
# added when the class-rename-residue basket was introduced, so its 9
# members (`nodes`, `edges`, `getData`, `importData`, `applyHistory`,
# `markMoved`, `markDirty`, `requestSave`, `__proto__`) rode the class-wide
# CLASS_RENAME_RESIDUE_DEFERRED basket instead of the reasoned one that
# actually applies to them. Confirmed the exact same mechanism as its
# siblings: `ViewBindings.ts:81` does `leaf.view as unknown as HostCanvasView`
# (the only cast boundary), `HostCanvasView.canvas: HostCanvas` flows from
# that live object with zero further cast, and `CanvasViewPatch.ts` reads/
# calls every one of the 9 members directly on it (`this.canvas.nodes`,
# `.markDirty()`, `.importData()`, `.requestSave()`, ...) against Obsidian's
# real, undocumented Canvas plugin object. Renaming any of them stops
# describing that object; the compiler cannot catch it, same as its four
# siblings above.
STRUCTURAL_EXTERNAL_TYPES = frozenset({
    'HostCanvasView', 'HostCanvasNode', 'HostCanvasEdge', 'CanvasItem',
    'CanvasNodeData', 'CanvasEdgeData', 'CanvasData', 'HostCanvas',
})

# Obsidian base classes. An OBSIDIAN_HOOKS name only counts as contract on a
# class that actually reaches one of these by `extends`, directly or through
# our own intermediate classes. Without this scoping the hook names matched on
# spelling alone, and `Banner.display` / `EmbedBanner.display` -- plain classes
# extending nothing, with their own `display(): boolean` convention -- were
# being excused as Obsidian's PluginSettingTab.display. Same failure shape as
# the generic verbs, one level subtler: the name really IS Obsidian's, just not
# on this class.
OBSIDIAN_BASE_TYPES = frozenset({
    'Plugin', 'Component', 'View', 'ItemView', 'FileView', 'TextFileView',
    'EditableFileView', 'MarkdownView', 'Modal', 'SuggestModal',
    'FuzzySuggestModal', 'AbstractInputSuggest', 'EditorSuggest',
    'PopoverSuggest', 'PluginSettingTab', 'SettingTab', 'MarkdownRenderChild',
    'MarkdownRenderer', 'Menu', 'BaseComponent', 'ValueComponent',
    'AbstractTextComponent', 'TextComponent', 'TextAreaComponent',
    'ToggleComponent', 'ButtonComponent', 'DropdownComponent',
    'SliderComponent', 'ColorComponent', 'SearchComponent',
    'ExtraButtonComponent', 'MomentFormatComponent', 'ProgressBarComponent',
})


# Interfaces we DECLARE conformance to (`implements X`) that are defined by an
# authority outside this codebase. Where OBSIDIAN_HOOKS scopes a name list by
# `extends`-reachability, this scopes by the `implements` clause -- the stronger
# signal, because the compiler enforces it: the class cannot rename these
# members and still satisfy the interface it says it satisfies. `tsc --noEmit`
# is the positive control (rename one and the build fails on the declaration
# itself, not merely at a call site).
#
# Both entries below were read off the REAL declarations, not recalled:
# `node_modules/typescript/lib/lib.es2015.collection.d.ts:19` +
# `lib.es2015.iterable.d.ts:141` for Map, and
# `node_modules/obsidian/obsidian.d.ts:6937` (TAbstractFile) + `:7113` (TFile).
#
# Deliberately NOT the same thing as TFILE_MIRROR_ADJUDICATED below: that basket
# is a DEFERRAL covering `Document`, which merely mirrors TFile's shape without
# declaring conformance and could in principle be renamed. `UnsavedFile` writes
# `implements TFile` and `VaultScopedMap` writes `implements Map<string, T>`, so
# for those two the spelling is externally fixed, not merely inconvenient --
# 'contract', per basket_name's own rule ("an external authority actually fixes
# THIS name on THIS declaration").
DECLARED_INTERFACE_CONTRACTS = {
    'Map': frozenset({'clear', 'delete', 'forEach', 'get', 'has', 'set',
                      'size', 'entries', 'keys', 'values'}),
    'TFile': frozenset({'vault', 'path', 'name', 'parent',
                        'stat', 'basename', 'extension'}),
}


def _declared_interface_contract(cls, name, bases):
    """True if `name` is fixed by an external interface `cls` declares."""
    if not cls:
        return False
    for iface in (bases or {}).get(cls, ()):
        if name in DECLARED_INTERFACE_CONTRACTS.get(iface, ()):
            return True
    return False


def _is_cm_plugin_value(cls):
    return cls.endswith('PluginValue')


def _reaches_obsidian_base(cls, bases, seen=None):
    """True if cls extends an Obsidian base type, directly or transitively."""
    if seen is None:
        seen = set()
    if cls in seen:
        return False
    seen.add(cls)
    for parent in bases.get(cls, ()):
        if parent in OBSIDIAN_BASE_TYPES:
            return True
        if _reaches_obsidian_base(parent, bases, seen):
            return True
    return False

# Wire / DB / on-disk shapes. A member is contract when the type DECLARING it
# is one of these -- no name list, no file scoping. Membership in the shape is
# the test, which is both narrower and more principled than the previous global
# WIRE_FIELDS list (`id`, `name`, `path`, `type`, `value`...): that list excused
# any field anywhere in five whitelisted files, including `RemoteFolderAuto.user`,
# a PRIVATE constructor-injected dependency that appears in no interface at all
# and is ours to rename.
#
# DELIBERATELY EXCLUDED: the domain interfaces in Relay.ts (`Relay`,
# `RemoteSharedFolder`, `RelayUser`, `RelaySubscription`, ...). Independent
# review argued they belong here, being "as externally load-bearing as the DAOs".
# They are not. `Relay` declares `folders: ObservableMap<string,
# RemoteSharedFolder>` and `subscriptions: ObservableMap<...>` -- live in-memory
# objects that cannot be serialised -- and nothing writes a `Relay` to disk or to
# the wire. It is our model OVER the DAOs, so renaming `Relay.name` costs one
# line in the DAO mapping and nothing else. Including it would have moved ~10
# names out of the work basket for free, which is the direction this gate must
# never drift.
#
# ALSO DELIBERATELY EXCLUDED: `License` / `LicenseMetadata` / `LicenseInfo`
# (EndpointManager.ts). A fourth review proposed them as an external contract,
# on the premise that the licence protocol is one EVC defined and third-party
# enterprise licence servers already implement. That premise is false, and the
# check is one command: upstream at the fork point d1b24af2 declares all three
# interfaces with byte-identical field sets, serving them from
# `.well-known/relay.md/license`. We inherited the shape and changed only the
# path segment to `.well-known/evc-team-relay/license`. So these are upstream's
# design copied verbatim -- the exact thing this gate exists to surface, not an
# obligation that survives it. `LicenseInfo` is not even on the wire: it is
# constructed locally from a decoded JWT. Excusing 8 names on an unverified
# claim about deployed customer servers is how the contract basket got a third
# too big twice already (606 -> 466 -> 395). If someone re-raises this, the
# burden is a named third party actually speaking our path, not plausibility.
# UPDATED (Mesh #a2f4027a): 6 of these entries held OLD names of types that
# were themselves renamed in a later wave -- same dead-reference failure as
# STRUCTURAL_EXTERNAL_TYPES above, found by the same measurement (does the
# entry name still resolve to a DECLARED type in our current tree? six did
# not). Each successor below is confirmed by reading both declarations, not
# assumed from the rename table alone -- `AuthSettings`/`LoginSettings` in
# particular is a byte-identical single-field shape (`provider: string |
# undefined`) in the same relative position (immediately before the class it
# configures), not just a name-similarity guess.
#   ClientToken          -> DocumentGrant   (relay/TokenShapes.ts)
#   FileToken            -> FileGrant       (relay/TokenShapes.ts)
#   TenantConfig         -> TenantRecord
#   EndpointSettings     -> TenantSettings
#   SharedFolderSettings -> VaultShareSettings
#   SyncFlags            -> AttachmentToggles
#   LoginSettings        -> AuthSettings
# The 10 PocketBase-record DAO names (FolderRoleDAO/ProviderDAO/RelayDAO/...)
# and DebugSettings/RelaySettings found NO successor at all -- not even at
# this task's low detection floor (>=3 shared non-generic members) -- which
# is consistent with this fork having moved off PocketBase's DAO layer
# entirely (the `pocketbase/` vendor directory itself is already gone, per
# VENDOR_DIRS's own note above) rather than merely renamed. Left as-is:
# genuinely dead is not the same defect as stale-successor, and guessing a
# replacement without evidence would be exactly the unverified-plausibility
# move this basket's own header comment already warns against.
WIRE_SHAPE_TYPES = frozenset({
    # PocketBase records -- these ARE the control-plane field names on the wire
    'FolderRoleDAO', 'ProviderDAO', 'RelayDAO', 'RelayInvitationDAO',
    'RelayRoleDAO', 'RelaySubscriptionDAO', 'RemoteFolderDAO', 'RoleDAO',
    'StorageQuotaDAO', 'UserDAO',
    # persisted plugin settings -- the data.json of every existing install
    'AuthSettings', 'TenantSettings', 'TenantRecord', 'RelayOnPremSettings',
    'LegacyRelayOnPremSettings', 'VaultShareSettings', 'RelaySettings',
    'DebugSettings',
    # shapes NESTED inside a persisted setting above. A field of a persisted
    # object is just as much an on-disk key as a top-level one -- renaming
    # `AttachmentToggles.images` breaks reading the data.json of every install
    # that ever toggled image sync, exactly like renaming a
    # `VaultShareSettings` field would. Reached via
    # `VaultShareSettings.sync?: AttachmentToggles` and
    # `RelayOnPremSettings.servers: RelayOnPremServer[]`.
    'AttachmentToggles', 'RelayOnPremServer',
    # relay token payloads. Added 2026-08-23 with the de-vendoring of
    # client/types.ts (Mesh #84bd2a91) -- these 18 field names WERE excused
    # before, but as "vendored third-party", which was the wrong reason. The
    # right one is that they are the token JSON itself, and the proof is a
    # direct unmapped cast: RelayCredentialCache.ts:202 does
    #     return (await response.json()) as FileGrant
    # so a renamed field reads `undefined` at runtime and the compiler cannot
    # object -- a cast asserts, it does not validate. The sibling path
    # (RelayOnPremTokenProvider.ts) builds a DocumentGrant field by field and
    # would survive a rename; one unmapped cast is enough to fix the names.
    # UPDATED (Mesh #a2f4027a): the TYPE names themselves were ClientToken/
    # FileToken when this was written ("ours and stay in the work basket");
    # both were renamed since, to DocumentGrant/FileGrant (relay/TokenShapes.ts),
    # and the file holding the unmapped cast was itself renamed
    # LiveTokenStore.ts -> RelayCredentialCache.ts. Member names below are
    # current; the type-axis rename this comment anticipated already happened.
    'DocumentGrant', 'FileGrant',
    #
    # W-axis2-tail (Mesh #6489249d). Seven types, each with its own unmapped
    # read/write, not grouped by guesswork from the shape of the name --
    # exactly the standard the FileGrant/DocumentGrant entry above set and
    # the axis-2 planning note (#df095a62) warned not to skip: enumerate the
    # syntactic forms (cast, type-predicate, persisted-map value type,
    # localStorage round-trip), then check each candidate against them.
    #
    # ItemRecordBase/AttachmentRecordBase (ItemKinds.ts): the CRDT wire
    # format itself, not merely persisted settings. FolderIndex.ts:54
    # declares `private records: Y.Map<ItemRecord>`, populated at :71 via
    # `this.crdt.getMap("filemeta_v0")` -- ItemRecord is PlainMeta<T> =
    # ItemRecordBase & {...} / FileMetaOf<T> = AttachmentRecordBase & {...}
    # (ItemKinds.ts:36,52). Every `.records.get(vpath)` / `.records.set(vpath,
    # meta)` call (FolderIndex.ts:125,220,233,238,259,354,461,463,499) reads
    # and writes these field names directly as the actual Yjs map-entry keys,
    # synced to every peer and persisted server-side with zero validation
    # layer -- a renamed field reads `undefined` on every already-shared
    # folder's pre-existing entries forever, the CRDT equivalent of the
    # unmapped-cast test.
    'ItemRecordBase', 'AttachmentRecordBase',
    #
    # LicenseRecord (TenantRegistry.ts:66): `isLicense()` (:105-111) type-
    # guards an incoming HTTP body via `"license" in candidate` -- a bare
    # string-literal key check, not a mapped validator, so `license` is the
    # wire key even more directly than an unmapped cast (the literal string
    # itself IS the check). `extractLicenses()` (:119) builds the returned
    # array straight from that guard over `await response.json()` (:290) --
    # `id`/`url` arrive on the same untyped body with no separate mapping.
    #
    # LicenseClaims (TenantRegistry.ts:84, `extends JWTPayload` from `jose`):
    # `verifySignedToken()` (:224) returns `jwtVerify(...)`'s decoded
    # `payload` typed as `Promise<LicenseClaims>` with no field-by-field
    # construction -- an implicit structural cast on a real signed external
    # artifact (the JWT body), not something this function's return type can
    # validate. `apiUrl`/`authUrl`/`customer`/`logo` are read directly off
    # that payload throughout the file (:362-380,449-453,511-532) -- a
    # renamed field reads `undefined` regardless of what the JWT (issued by
    # the license side of our own system, but not reissued by renaming a
    # client-side interface) actually contains.
    'LicenseRecord', 'LicenseClaims',
    #
    # ServiceHealthReport (ServiceHealthMonitor.ts:7): `response.json as
    # ServiceHealthReport | undefined` (:133) -- the same unmapped-cast shape
    # as FileGrant/DocumentGrant above, on a different HTTP response.
    'ServiceHealthReport',
    #
    # CredentialEntry (CredentialCache.ts:62): persisted, not just in-memory.
    # RelayCredentialCache.ts wires `getPersistedTokens` to
    # `new VaultScopedMap<CredentialEntry<DocumentGrant>>(...)`; VaultScopedMap
    # (VaultScopedMap.ts:22) loads its backing blob via
    # `this.app.loadLocalStorage(this.blobKey) as Record<string, T> | null`
    # -- an unmapped cast on `App#loadLocalStorage`'s return, the same
    # persisted-settings shape as the `AttachmentToggles`/`RelayOnPremServer`
    # entries above, just reached through Obsidian's local-storage API
    # instead of `data.json`. A renamed field on `friendlyName`/`token`/
    # `expiryTime`/`attempts` reads `undefined` for every already-cached
    # credential on every existing install.
    'CredentialEntry',
    #
    # ProtocolLinkParams (main.ts:2097, local to registerObsidianProtocolHandler's
    # setup): `e as unknown as ProtocolLinkParams` (:2105,:2114) -- Obsidian's
    # own `obsidian://` deep-link handler hands this function a real external
    # payload (the URL's parsed query string) via a double unmapped cast, the
    # strongest form of this test. (Being function-scoped is an axis-1
    # question, already answered by that axis renaming the TYPE itself
    # Parameters -> ProtocolLinkParams, `PREDECESSOR_TYPES` below -- unrelated
    # to whether ITS FIELDS are wire, which is what this entry answers.)
    'ProtocolLinkParams',
})

# KNOWN LIMITATION -- this list is NOT transitive; nesting is hand-traced.
# The membership test walks one level: a member is contract when the type
# DECLARING it is named above. Nothing computes the closure over field types,
# so a persisted shape nested inside a persisted shape has to be added here by
# hand, and a future one will be missed until someone notices. Deliberate:
# an automatic closure would have to decide which field types to follow into,
# and following a field typed `ObservableMap<...>` would drag live in-memory
# objects into the contract basket -- the one direction this gate must never
# drift. Two hand-traced entries with a stated reason beat a closure that
# silently excuses names nobody re-examines. Revisit if the count grows.

# ---------------------------------------------------------------------------
# W0b adjudication (Mesh #1268d259). Three tests, applied in this order:
#
#   B / contract  — the NAME ITSELF is the binding: renaming it breaks something
#                   outside our control. Almost nothing qualifies. A type whose
#                   *shape* mirrors an external API does NOT: renaming
#                   `interface CanvasData` breaks nothing, because what Obsidian
#                   fixes is the JSON field names, not our identifier. Measured:
#                   exactly ONE declaration in `src/` sits inside `declare
#                   global`/`declare module`, and that one is below.
#
#   C / convergent — an independent author writing this from scratch lands on the
#                   same word. Claimed only with EVIDENCE, never on the feel of
#                   the word: either the name is declared by >=2 unrelated
#                   packages in `node_modules` (`obsidian` and
#                   `eslint-plugin-obsidianmd` collapse to one authority — they
#                   ship the same API), or it is a DOM element property that a
#                   Svelte component forwards as a prop (checked against
#                   `typescript/lib/lib.dom.d.ts`).
#
#   A / work      — everything else. 209 of our 236 shared type names are
#                   declared by ZERO unrelated packages; they are ours to rename
#                   and that is the point of the gate.
#
# The bias is deliberate and the history explains it: the first draft of the
# contract basket was a third too generous (606 -> 388) and three independent
# review passes moved 211 more names back to work. Every defect ran one way,
# "greener than truth". So a name enters B or C only with a reason that names an
# authority or a corpus count -- "looks generic" is not a reason.
CONTRACT_TYPES = frozenset({
    # `declare global { interface Window }` in Patcher.ts -- a global
    # augmentation binds BY NAME. Rename it and it stops augmenting `Window`.
    # The only true contract name on this axis.
    'Window',
})

# Convergent by ONE of exactly two tests, each carrying its own evidence:
#
#   corpus   >=2 unrelated packages in `node_modules` really DECLARE the name.
#            Counted by a scanner that strips comments first, so prose inside a
#            JSDoc `@example` block never counts -- that alone cost the first
#            draft three names. Counts below are declaring packages after
#            collapsing (`obsidian` + `eslint-plugin-obsidianmd` = one
#            authority; a vendored copy is attributed to the package it copies).
#
#   platform the SOLE declaring package is a platform this plugin is BUILT ON
#            (`obsidian`, `svelte`), and it declares the SAME NAME for the SAME
#            CONCEPT -- verified by opening both declarations, not by the word.
#            This is the innocent cause from the card's category B: we and
#            upstream reach for the word because we both build on that platform.
#            Naming this test explicitly is a correction -- these names used to
#            ride in on the corpus test, which they do not pass.
#
# An icon component is NOT a declaring authority. `lucide-svelte` ships one
# `.svelte.d.ts` per glyph, so it "declares" `User`, `Settings`, `Key`, `Link`
# and a few hundred more nouns. That is a naming coincidence of a sprite sheet,
# the same class of hit that keeps `TokenStore` out (below).
CONVERGENT_TYPES = frozenset({
    # -- corpus test -------------------------------------------------------
    'Callback',          # 7: @jest/fake-timers, catering, escalade, tapable, …
    'Path',              # 6: chokidar, path-scurry, readdirp, typescript, …
    'Document',          # 5: @types/tern, obsidian, parse5, typescript, yaml
    'ValidationError',   # 4: @types/json-schema, ajv, jest-validate, lib0
    'Listener',          # 3: @types/node, event-target-shim, svelte
    'Settings',          # 2: @types/node, @typescript-eslint/utils
                         #    (a 3rd hit is the lucide-svelte icon -- discounted)
    'CloseEvent',        # 2: typescript, undici-types
    'LogLevel',          # 2: esbuild, typescript
    'LogEntry',          # 2: @humanfs/core, @jest/console
    # -- platform test -----------------------------------------------------
    # Obsidian's own canvas file format: `obsidian/canvas.d.ts` declares these
    # three names for this exact JSON. Any plugin describing a canvas writes
    # them. We declare our own mirrors in CanvasView.ts.
    'CanvasData', 'CanvasNodeData', 'CanvasEdgeData',
    # Svelte's store contract. `svelte/src/runtime/store/public.d.ts` declares
    # `type Subscriber<T> = (value: T) => void` and `type Unsubscriber = () =>
    # void`; ours in observable/Observable.ts are the same two signatures,
    # because that IS the contract a Svelte store implements.
    'Subscriber', 'Unsubscriber',
    # DELIBERATELY NOT HERE, though the corpus does hit it: `TokenStore`
    # (@typescript-eslint/utils, jsonc-eslint-parser). Both hits are the ESLint
    # family and neither means what ours means -- ours is the relay token cache.
    # A coincidental collision is not convergence, and admitting it would be
    # exactly the "greener than truth" move this basket exists to resist.
    #
    # Also deliberately absent, each demoted to work on a MEASUREMENT that
    # contradicted its first-draft comment:
    #   Dependency  1 pkg (type-fest, a package.json schema field). The claimed
    #               second author, ansi-escapes, declares it nowhere.
    #   UUID        1 pkg (@types/node). `obsidian` does not declare it.
    #   Parameters  1 pkg (typescript's built-in utility type). Ours is a local
    #               interface for our protocol-handler URL params -- not that.
    #   User        1 pkg, and it is the lucide-svelte glyph. Every type-fest
    #               hit is inside a JSDoc @example block.
    #   ViewState   `obsidian` declares the NAME but for another CONCEPT: theirs
    #               is a workspace-leaf view state {type,state,active}, ours is
    #               the differ's {file1,file2,showMergeOption}. Shared spelling,
    #               nothing more -- the platform test needs the same concept.
    #   Observable  1 pkg (lib0), a transitive utility of yjs rather than a
    #               platform we build on; ours is our own class over HasLogging.
})

# Type-predicate EXPORTS whose narrowed type is itself in CONVERGENT_TYPES above
# (W6b, gate4 #f3eb7b30). A guard's whole reason to exist is naming the type it
# narrows to -- `isDocument`'s signature is `(file?: IFile): file is Document`,
# and `Document` sits in CONVERGENT_TYPES on its own corpus test (5 independent
# packages: @types/tern, obsidian, parse5, typescript, yaml). Renaming the guard
# while `Document` itself stays put buys nothing: the pair (type, guard) reads as
# one unit, and an independent author narrowing to the SAME convergent type would
# reach for the SAME guard name for the SAME reason we did. That is a cosmetic
# symbol shuffle for the metric's sake -- the exact move gate 4's own docstring
# (line ~9, "no longer a fork in substance") disclaims, and moving it here rather
# than leaving it in `work` says so explicitly instead of quietly renaming it.
#
# Deliberately its own frozenset, not folded into CONVERGENT_EXPORTS above: that
# basket's documented test is "reaches a native DOM element" (a Svelte-prop
# question) and does not apply here -- an export could clear THIS test and fail
# that one, or vice versa. Keeping them separate keeps each test legible on its
# own terms instead of one entry silently borrowing the other's justification.
CONVERGENT_TYPE_GUARD_EXPORTS = frozenset({
    'isDocument',   # (file?: IFile): file is Document -- Document.ts
})

# Directory names every Svelte/TS project of this shape uses. Nobody reads
# `components/` as evidence of a fork.
CONVERGENT_DIRS = frozenset({'components', 'ui', 'utils'})

# Svelte props named after a DOM attribute the component actually FORWARDS.
# Both halves are measured, and each half killed names the first draft admitted:
#
#   1. the name is an IDL property of a DOM *element* interface in
#      `typescript/lib/lib.dom.d.ts` (comments stripped first). Being somewhere
#      in that file is not enough -- `items` is on DataTransfer, `details` on
#      PaymentResponse, `progress` on ComputedEffectTiming, `element` on
#      XSLTProcessor. None is an element property, so no component can be
#      forwarding one. That test alone removed 11 of the original 24.
#
#   2. the prop reaches a NATIVE element tag, not just a child component or a
#      script branch. `size` ends at `style:width={size}`, `type` at
#      `class="toast toast-{type}"`, `title` and `text` and `name` are rendered
#      as content, `label` goes to `aria-label` (a different attribute), `close`
#      is our callback, and `autofocus` terminates in `if (autofocus && inputEl)`
#      -- an imperative focus call, never an attribute.
#
# `remote` remains excluded on the same reasoning it always was: ours is the
# remote-shared-folder domain concept and the DOM collision is incidental.
CONVERGENT_EXPORTS = frozenset({
    'alt',          # <img {alt}>            Avatar.svelte
    'disabled',     # <select|input {disabled}>  7 native sites
    'placeholder',  # <input {placeholder}>   3 native sites
    'value',        # <select {value}>, <option value=…>  5 native sites
})

# Files carrying a convergent type as their whole reason for existing. Listed by
# name rather than derived, so adding a convergent type never silently annexes a
# file as a side effect.
# `User.ts` and `observable/Observable.ts` were here because `User` and
# `Observable` were convergent types. Both types were demoted to work on
# measurement, so the file exemptions go with them -- otherwise the file axis
# would quietly re-exempt exactly what the type axis just demoted.
CONVERGENT_FILES = frozenset({
    'Document.ts',
})

# Files whose path is fixed by an external convention we didn't choose, not by
# an owned convergent TYPE inside them (that's CONVERGENT_FILES above -- kept
# separate so the two reasons don't get conflated: a file here can carry
# zero convergent types of its own).
#
# `main.ts`: the official Obsidian plugin template
# (obsidianmd/obsidian-sample-plugin) pins `entryPoints: ['src/main.ts']`, and
# our own independently-written evc-local-sync-plugin sibling arrived at the
# same path from the same template -- convergence on the template, not a
# fork tail. (The actual fork tail in this file was `export default class
# Live`, and gate4 W7d retires that name.) Also load-bearing for
# check-verbatim-distinct.py's ADJUDICATED basket, which is keyed on this
# exact filename -- renaming it would fail that gate, not just this one.
PLATFORM_CONVENTION_FILES = frozenset({
    'main.ts',
})

SRC_EXT = ('.ts', '.svelte', '.js')

# ---------------------------------------------------------------------------
# Declaration extraction. Regex, not a TS parser: it must run with no toolchain
# and its misses are visible via --show-samples rather than hidden in a tree.
# ---------------------------------------------------------------------------
RE_TYPE = re.compile(
    r'^\s*(?:export\s+(?:default\s+)?)?(?:declare\s+)?(?:abstract\s+)?'
    r'(class|interface|enum)\s+([A-Za-z_$][\w$]*)')
# `type` is split out from RE_TYPE above because it is ALSO valid TS syntax for
# an import specifier -- `type RecordModel,` alone on a line inside a
# multi-line `import { ... } from "pocketbase"` block matches
# `^\s*(?:export\s+)?...(type)\s+(name)` perfectly, with nothing distinguishing
# it from an actual `type X = ...` alias declaration. A real alias always has
# `=` (or `<` opening its generic parameter list, which itself resolves to `=`)
# immediately after the name; an import specifier's name is instead followed
# by `,`, end-of-line, or ` as <alias>`. The lookahead below is that check.
# This also catches the OTHER shape the unguarded regex mis-parsed: a plain
# type-assertion expression `type as SyncFileType` (SharedFolder.ts) reads as
# keyword=`type`, name=`as` under the old regex -- `as` is a valid identifier,
# so it silently entered the type basket as a declared name. The `<`/`=`
# lookahead rejects this the same way, since `as` is followed by whitespace
# then `SyncFileType`, not `<` or `=`.
RE_TYPE_ALIAS = re.compile(
    r'^\s*(?:export\s+)?(?:declare\s+)?'
    r'type\s+([A-Za-z_$][\w$]*)\s*(?=[<=])')
RE_CONST_ENUM = re.compile(
    r'^\s*(?:export\s+)?declare\s+const\s+enum\s+([A-Za-z_$][\w$]*)')
RE_EXPORT_FN = re.compile(
    r'^\s*export\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*'
    r'([A-Za-z_$][\w$]*)')
RE_EXPORT_VAR = re.compile(
    r'^\s*export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)')
RE_CLASS_OPEN = re.compile(
    r'^\s*(?:export\s+(?:default\s+)?)?(?:declare\s+)?(?:abstract\s+)?'
    r'(?:class|interface)\s+([A-Za-z_$][\w$]*)')
# `extends Foo` / `implements Bar, Baz` on the declaration line. Generic args
# are dropped: `extends Observable<Relay>` reaches the base `Observable`.
RE_EXTENDS = re.compile(r'\bextends\s+([A-Za-z_$][\w$.]*)')
RE_IMPLEMENTS = re.compile(r'\bimplements\s+([^{]+)')

MOD = r'(?:public\s+|private\s+|protected\s+|static\s+|readonly\s+|abstract\s+|override\s+|declare\s+|async\s+|get\s+|set\s+)*'
RE_MEMBER_METHOD = re.compile(r'^\s*' + MOD + r'([A-Za-z_$#][\w$]*)\s*[(<]')
RE_MEMBER_FIELD = re.compile(
    r'^\s*' + MOD + r'([A-Za-z_$#][\w$]*)\s*[?!]?\s*[:=](?![=>])')
# A constructor's parameter list sits at the same BRACE depth as the class body
# (parens do not open a brace), so a plain `args: ActionLineArgs,` parses as a
# field. It is not one. TypeScript's parameter properties -- `private app: App,`
# -- ARE fields, and are kept: the visibility modifier is what creates them.
# Spot-checked against differ/actionLine.ts, where both forms appear.
RE_VISIBILITY = re.compile(r'^\s*(public|private|protected|readonly)\s')

# Statements that look like a member declaration but are control flow or a call.
NOT_A_MEMBER = frozenset({
    'if', 'for', 'while', 'switch', 'catch', 'return', 'throw', 'new',
    'await', 'typeof', 'delete', 'case', 'do', 'else', 'try', 'yield',
    'import', 'export', 'function', 'class', 'interface', 'enum', 'type',
    'const', 'let', 'var', 'this', 'super',
})


def _scan_header(text, angle_depth=0):
    """Find the class BODY brace, ignoring any `{` inside a generic parameter
    list. Returns (index_of_body_brace_or_-1, angle_depth_after_this_text).

    `class Foo<T extends { bar: string }>` opens a brace that is NOT the body,
    and treating it as one drops the whole class: the header resolves early,
    the class is pushed at the wrong depth, and the next line pops it straight
    back off before the real body arrives. Constructible and confirmed; it is
    the same whole-class loss the multi-line buffering was added to fix,
    reopened through a different door. Angle depth carries ACROSS lines, so a
    `Base<{` split over four lines is tracked too.

    `=>` is skipped so an arrow type inside a header does not close a bracket
    that was never opened.
    """
    for i, c in enumerate(text):
        if c == '<':
            angle_depth += 1
        elif c == '>':
            if i and text[i - 1] == '=':
                continue                      # `=>`, not a closing bracket
            if angle_depth:
                angle_depth -= 1
        elif c == '{' and angle_depth == 0:
            return i, angle_depth
    return -1, angle_depth


def _strip_generics(text):
    """Drop balanced `<...>` sections so `extends`/`implements` are read from
    the real heritage clause. `NamespacedSettings<T extends object, Parent
    extends object = Record<...>> extends Observable<T>` otherwise yields
    `object` as the base -- RE_EXTENDS matches the FIRST `extends`, which is a
    type-parameter bound, and the actual base `Observable` is never recorded.
    """
    out, depth = [], 0
    for i, c in enumerate(text):
        if c == '<':
            depth += 1
        elif c == '>' and not (i and text[i - 1] == '='):
            if depth:
                depth -= 1
            else:
                out.append(c)
        elif depth == 0:
            out.append(c)
    return ''.join(out)


def _strip_svelte(text):
    """Keep only <script> bodies of a .svelte file; markup has no declarations."""
    blocks = re.findall(r'<script[^>]*>(.*?)</script>', text,
                        re.S | re.I)
    return '\n'.join(blocks) if blocks else ''


def _decomment(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return '\n'.join(re.sub(r'//.*$', '', l) for l in text.split('\n'))


def extract(path):
    """-> (types:set, exports:set, members: {Class: set(member)})"""
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            raw = fh.read()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return None
    if path.endswith('.svelte'):
        raw = _strip_svelte(raw)
    raw = _decomment(raw)

    types, exports = set(), set()
    members = defaultdict(set)
    zero_arg = defaultdict(set)   # methods declared with an empty parameter list
    bases = defaultdict(set)
    stack = []          # (class_name, brace_depth_at_open)
    depth = 0
    # A class/interface header does not have to fit on one line. Measured in
    # our own src/: `export class SyncFile`, `ObservablePermission`,
    # `RemoteFolderAuto`, `RelaySubscriptionAuto`, `NamespacedSettings` and six
    # bare interfaces in Relay.ts all put `extends`/`implements` -- or just the
    # `{` -- on the NEXT line. The first draft only opened a class body when the
    # keyword and the `{` shared a physical line, so those classes were never
    # pushed onto the stack at all and their ENTIRE member set silently vanished
    # from both trees. That is an undercount of the work basket, in the one
    # direction that flatters us, and it hid ~14 shared names on SyncFile alone.
    # So: buffer the header until its opening brace arrives.
    pending = None      # (class_name, accumulated_header_text)
    PENDING_MAX_LINES = 10
    for line in raw.split('\n'):
        stripped = line.strip()
        m = RE_TYPE.match(line)
        if m:
            types.add(m.group(2))
        m = RE_TYPE_ALIAS.match(line)
        if m:
            types.add(m.group(1))
        m = RE_CONST_ENUM.match(line)
        if m:
            types.add(m.group(1))
        m = RE_EXPORT_FN.match(line)
        if m:
            exports.add(m.group(1))
        m = RE_EXPORT_VAR.match(line)
        if m:
            exports.add(m.group(1))

        opening = RE_CLASS_OPEN.match(line)
        header, cname = None, None
        if opening:
            cname = opening.group(1)
            bi, adepth = _scan_header(line)
            if bi >= 0:
                header = line
            else:
                pending = (cname, line, 1, adepth)
                continue
        elif pending is not None:
            pname, ptext, pcount, pdepth = pending
            bi, adepth = _scan_header(line, pdepth)
            ptext = ptext + ' ' + line
            if bi >= 0:
                cname, header, pending = pname, ptext, None
            elif pcount >= PENDING_MAX_LINES:
                pending = None      # not a header after all; don't swallow the file
            else:
                pending = (pname, ptext, pcount + 1, adepth)
                continue

        # members of the innermost open class/interface body
        if stack and depth == stack[-1][1] + 1 and header is None:
            bare_param = (stripped.endswith(',')
                          and not RE_VISIBILITY.match(line))
            for rx in (RE_MEMBER_METHOD, RE_MEMBER_FIELD):
                mm = rx.match(line)
                if mm:
                    nm = mm.group(1)
                    if (nm not in NOT_A_MEMBER and not nm.startswith('#')
                            and not (rx is RE_MEMBER_FIELD and bare_param)):
                        members[stack[-1][0]].add(nm)
                        if rx is RE_MEMBER_METHOD:
                            after = line[mm.end(1):]
                            op = after.find('(')
                            cl = after.find(')', op + 1) if op >= 0 else -1
                            if op >= 0 and cl > op and not after[op + 1:cl].strip():
                                zero_arg[stack[-1][0]].add(nm)
                    break

        opens = line.count('{')
        closes = line.count('}')
        if header is not None:
            heritage = _strip_generics(header)
            ext = RE_EXTENDS.search(heritage)
            if ext:
                bases[cname].add(ext.group(1).split('.')[-1])
            impl = RE_IMPLEMENTS.search(heritage)
            if impl:
                for part in impl.group(1).split(','):
                    part = re.sub(r'<.*', '', part).strip()
                    if re.fullmatch(r'[A-Za-z_$][\w$.]*', part or ''):
                        bases[cname].add(part.split('.')[-1])
            stack.append((cname, depth))
            depth += opens - closes
            continue
        depth += opens - closes
        while stack and depth <= stack[-1][1]:
            stack.pop()
        if depth < 0:
            depth = 0
    return types, exports, dict(members), dict(bases), dict(zero_arg)


def walk_tree(root):
    files, dirs = set(), set()
    for dp, dns, fns in os.walk(root):
        rel_dir = os.path.relpath(dp, root).replace(os.sep, '/')
        if rel_dir != '.':
            dirs.add(rel_dir)
        for fn in fns:
            if fn.endswith(SRC_EXT):
                rel = os.path.relpath(os.path.join(dp, fn), root)
                files.add(rel.replace(os.sep, '/'))
    return files, dirs


def collect(root, files):
    types, exports = {}, {}
    members = defaultdict(lambda: defaultdict(set))
    bases = defaultdict(set)
    zero_arg = defaultdict(set)
    for rel in sorted(files):
        got = extract(os.path.join(root, rel))
        if got is None:
            continue
        t, e, m, b, z = got
        for cls, parents in b.items():
            bases[cls] |= parents
        for cls, names in z.items():
            zero_arg[cls] |= names
        for n in t:
            types.setdefault(n, rel)
        for n in e:
            exports.setdefault(n, rel)
        for cls, ms in m.items():
            for name in ms:
                members[cls][name].add(rel)
    return types, exports, members, dict(bases), dict(zero_arg)


# ---------------------------------------------------------------------------
# W8 adjudication (Mesh #4a73e623, decided in the wave's own comment). Member-
# level exceptions, gate 3's ADJUDICATED convention applied to this axis.
# None of these is 'contract': nothing external fixes any of these names, we
# are free to rename every one of them. They sit here because renaming them
# THIS WAVE costs more than this wave's board (Document.ts,
# SettingsPersistence.ts, TenantRegistry.ts) buys, not because an authority
# outside our control requires the spelling. A future wave can move any
# entry back to work by deleting it here and doing the rename.
#
# W9 (Mesh #cf371fdf) closed 4 of the 15 W8 entries: `SyncableEntry.{cleanup,
# move}` -> `dispose`/`relocate`, `MimeTyped.mimetype` -> `mimeType`, and
# `Settings.notifyListeners` -> `notifySubscribers` (OWN_BASE_CLASS_ADJUDICATED,
# now empty and removed, dict deleted below). `SyncableEntry.{connect,destroy,
# path}` were NOT closed then; W10 (Mesh #d9031010 + #b1cd12e0) closed all
# three in the dedicated pass W9 asked for.
#
#   - `connect`/`destroy`: CLOSED W10, 2026-08-27 (Mesh #d9031010) ->
#     `bringOnline`/`dismantle`. The hazard W9 named was real:
#     `ProviderBacked.connect()`/`.destroy()` also call
#     `this._provider.connect()` / `this._provider.destroy()` (a REAL
#     third-party y-sweet provider) and `this.ydoc.destroy()` (Yjs's own
#     Y.Doc), so a blind word-level rename would have corrupted those external
#     calls. Done instead by resolving every `connect`/`destroy` identifier to
#     its DECLARATION through the TS checker and rewriting only the 79 that
#     land on SyncableEntry/ProviderBacked/Document/CanvasDocument/VaultShare/
#     TrackedFolder/AttachmentFile; the 247 that land on YSweetProvider, lib0
#     `Observable` (Y.Doc), `IndexeddbPersistence`, `LazyValue`, Svelte's
#     action contract, VaultShareSettings' persisted `connect` field, and the
#     ~40 unrelated `destroy()`-bearing classes were left alone. Two sites the
#     checker could not see were handled by hand: a `.svelte` call site (not
#     in the TS program) and two `Object.defineProperty(fakeDoc, "connect")`
#     test stubs (string-literal member names). Guarded by
#     `__tests__/providerExternalApiNames.test.ts`, which asserts at runtime
#     that the external objects are still reached under `connect`/`destroy`
#     and never under the new names -- something `tsc` cannot check on a
#     structurally-typed provider.
#   - `path`: CLOSED W10, 2026-08-27 (Mesh #b1cd12e0) -- renamed to
#     `entryPath` on `SyncableEntry` and every implementor, together with
#     `Document`'s six TFILE_MIRROR names (that class's row removed from the
#     basket below; `AttachmentFile`'s six -- added independently by W17,
#     after this branch forked -- remain open, see below). The blocker W9
#     recorded here was the unguarded read in `FileDiffView`; it was fixed
#     first -- `DiffViewState.file1/file2` now type as
#     `TFile | Document | UnsavedFile` and both reads narrow on
#     `instanceof Document`, matching what `modify()`/`readContent()` in that
#     file already did -- under new test coverage
#     (`__tests__/fileDiffView.test.ts`, the class had none), and only then
#     was the rename applied. `ProviderBacked.path` moved with it: left
#     behind, it would have kept answering `doc.path` with a permanent
#     `undefined` through inheritance, which is the same silent read one
#     level down. `VaultShare.path` deliberately did NOT move (a share is the
#     container entries are addressed against, not an entry) and overrides
#     `getVaultPath()` instead.
#
# `guid`/`disconnect` (added W14, Mesh #0b72373d -- restated as W17 a few
# lines below in an earlier pass of this comment) and `Disposable.destroy`
# were OUT OF SCOPE for W10, which touched only `connect`/`destroy`/`path`.
# `guid`/`disconnect` CLOSED (Mesh #fe4e6843, W22 follow-up): `SyncableEntry`
# renamed to `entityGuid`/`goOffline` together with every declaration that
# shared its exact spelling -- not "four implementors with their own
# copies" as first assumed, but three thin compat aliases (`Document`,
# `CanvasDocument` onto `ProviderBacked`'s already-renamed
# `entityGuid`/`goOffline`; deleted outright, zero new code needed) plus two
# genuinely independent properties (`AttachmentFile`, backed by its own
# `_localGuid`; `TrackedFolder`, a real constructor param -- both renamed in
# place). `guid`'s IndexedDB wire hazard turned out NOT to be reachable
# through the interface at all: `UnsavedFileStore.persistUnsaved(guid,
# contents)` (UnsavedFile.ts) takes a plain string and builds its own record
# via the object-shorthand `{ guid, contents }`, so the STORED FIELD NAME
# comes from that local PARAMETER, never touched by this rename (callers
# already passed `entityGuid`'s value positionally, before and after).
# Guarded instead by a new round-trip test, `__tests__/UnsavedFile.test.ts`,
# proving the persisted record's own field is genuinely named `guid` (a
# renamed *parameter* there, independent of this interface, is the actual
# hazard -- confirmed red/green by trying it).
OWN_INTERFACE_ADJUDICATED = {
    # W14 (Mesh #0b72373d). `Disposable` (src/ui/treeVisitor.ts:22) is OURS --
    # one method, `destroy(): void` -- and is therefore renameable in
    # principle, which is exactly why it sits here rather than in
    # DECLARED_INTERFACE_CONTRACTS above. It is not renamed THIS wave because
    # the name is not `SyncQueueIndicator`'s to change alone: five sibling
    # decorations in the same file implement it (FolderLiveIndicator,
    # FolderStatusPill, FileUploadPill, UnsyncedFilePill,
    # DocumentConnectionStatus), and it is consumed GENERICALLY, through the
    # interface rather than through any concrete class -- `toggleDecoration`
    # (treeVisitor.ts:91) and `FileExplorerWalker.destroy` (:106) both call
    # `.destroy()` on a `Disposable` they never narrow. Renaming one
    # implementor is a compile error; renaming the interface reaches
    # treeVisitor.ts, FileExplorerWalker.ts and ExplorerDecorationCoordinator.ts,
    # none of which is on this wave's board and the last of which is itself
    # still in CLASS_RENAME_RESIDUE_DEFERRED (i.e. a later wave will have to
    # open that file anyway, and can carry the interface rename then).
    #
    # Note the collision that makes a blind pass dangerous here and forced the
    # per-call-site check: `destroy()` in these same files is ALSO Svelte's
    # `$destroy()`, `SiblingAppearanceObserver.destroy()`, `Y.Doc.destroy()`
    # and `ProviderBacked.destroy()` -- four unrelated authorities sharing one
    # verb.
    'Disposable': frozenset({'destroy'}),
    # W-axis2-C (Mesh #0de35c1c). `PropertiesEditorSync`/`ReadingViewSync`
    # both `implements DocumentSurfaceSync` (viewSync/DocumentSurfaceSync.ts)
    # -- `render`/`destroy` are declared on the interface (:11,:14), not
    # chosen freely by either implementor. The interface is consumed
    # generically by `ViewSurfaceBridge` (viewSync/ViewSurfaceBridge.ts:54),
    # which builds `surfaceRenderers: DocumentSurfaceSync[]` from both
    # concrete classes and calls `.render()`/`.destroy()` through that
    # interface type -- renaming one implementor's spelling without the
    # other (or the interface) is a compile error against that shared array.
    # `bases[cls]` verified to actually carry the interface name for both
    # (grep confirms `implements DocumentSurfaceSync` on both class
    # declarations), not assumed from the `implements` clause being present
    # in source.
    'DocumentSurfaceSync': frozenset({'render', 'destroy'}),
    # W-axis2-B (Mesh #d934b4b9). Notifier<T> `implements Subscribable<T>`
    # (notifiers/Notifier.ts:34) -- `on`/`off` are declared on the interface
    # (:13,15), not chosen freely by Notifier itself. Upstream's own
    # `IObservable` declares `on, subscribe, off, unsubscribe`; our
    # `Subscribable` already diverged on the fourth member
    # (`unsubscribe`->`dropSubscriber`, a prior wave), but `on`/`subscribe`/
    # `off` remain -- renaming them is an interface-contract decision, not a
    # per-implementor one, and every one of Notifier's 9 subclasses
    # (FeatureToggleState, AuthSession, Settings, SettingsScope,
    # AttachmentFile, KindRegistry, FolderIndex, NotifierSet, NotifierMap)
    # calls `.on(`/`.off(` polymorphically through the base type -- renaming
    # the interface without renaming every one of those call sites in the
    # same change is a compile error, and `.svelte` consumers wouldn't even
    # give tsc the chance to catch it (`SRC_EXT` includes `.svelte`, but tsc's
    # own tsconfig scope does not, per #00631a54). Deferred rather than
    # renamed; not this wave's decision to make alone.
    'Subscribable': frozenset({'on', 'off'}),
}
# NOTE (W20, Mesh #b8f7818d): SettingsScope<T> extends Notifier<T>
# (src/SettingsPersistence.ts:246) and overrides `destroy()`/`subscribe()`
# from the base -- already covered generically by
# OWN_BASE_CLASS_ADJUDICATED['Notifier'] below (every direct Notifier
# subclass, not a SettingsScope-specific entry), not a gap needing its own
# OWN_INTERFACE_ADJUDICATED row. `subscribe` is separately excused by
# SVELTE_STORE_MEMBERS.

# TFILE_MIRROR_ADJUDICATED (`Document.{name,extension,basename,stat,vault,
# parent}`) is CLOSED W10, 2026-08-27 (Mesh #b1cd12e0) and its row removed
# below. `Document` no longer mirrors `TFile`'s shape: the six are now
# `docLabel`, `docSuffix`, `docStem`, `fileMetrics`, `obsidianVault` and
# `parentFolder`, so the class is no longer structurally assignable to
# `TFile` at all (`find-tfile-document-duck-typing.mjs` prints
# `Document assignable to TFile (structural)? false`). `AttachmentFile`'s
# identical six-member row (added W17, Mesh #d1ec15d8, after this branch
# forked -- see below) is NOT part of W10's scope and remains open.
#
# W9's reason for deferring `Document`'s row was that the tsc-iterate method
# cannot rename these words safely on its own, because the same words are the
# real field names on every genuine `TFile` in this codebase. That held. What
# made the rename safe was doing it in the other order: first widen the one
# slot that accepted a `Document` as a `TFile` (`DiffViewState.file1/file2`)
# into an explicit union and narrow its reads, THEN rename -- after which tsc
# pointed at exactly one remaining site for `name` and 61 for `path`, and no
# site had to be found by grep. W9's confirmed consumer had no test coverage
# at all; it does now (`__tests__/fileDiffView.test.ts`), written and shown
# red against the renamed shape before the narrowing landed.
#
# UPDATE (W9, Mesh #cf371fdf): the prior version of this comment said "grep
# -rn 'as TFile\b|as unknown as TFile' src/ found zero casts, so no CONFIRMED
# duck-typed consumer exists on this tree today" -- THAT IS NOW KNOWN FALSE,
# not just theoretically incomplete. A type-aware scan (TS compiler API,
# `checker.isTypeAssignableTo` + walking every call-arg/assign/return/
# array-literal/object-literal site, proven live with an injected positive
# control before trusting its zero-findings run) found a real one:
# `ViewBindings.ts:580` and `y-codemirror.next/LiveEditPlugin.ts:109` both
# call `openDiffView({ file1: this.document, ... })` where `DiffViewState`
# (`src/fileDiff/fileDiffView.ts:24-26`) types `file1`/`file2` as `TFile` --
# structurally legal with zero cast, since `Document` has every `TFile`
# field. `FileDiffView` itself reads `this.state.file1.name` (tab title,
# line 74) and `.path` (diff header, lines 133-134) directly on that
# TFile-typed slot, unguarded -- unlike `modify()`/`readContent()` in the same
# file, which DO check `instanceof Document` first before touching anything
# document-specific. Renaming `Document.name` (or `.path`, see
# OWN_INTERFACE_ADJUDICATED above) today would make that tab title/diff
# header silently read `undefined` for a Document-backed conflict, with zero
# compile error -- exactly the risk this basket was already guessing at, now
# with a name and two line numbers. The absence-of-explicit-cast check this
# comment used to lean on cannot see this class of site BY CONSTRUCTION: the
# assignment needs no cast to compile, so grepping for `as TFile` was never
# going to find it regardless of how carefully it was run.
#
# UPDATE (W17, Mesh #d1ec15d8): `AttachmentFile` added. Its case is stronger
# than `Document`'s above, not just similar: `AttachmentFile` carries an
# EXPLICIT `implements TFile` clause (`AttachmentFile.ts`), so these six
# field names are not merely a duck-typing risk somewhere downstream -- they
# are a compile-time contract on the class declaration itself. Renaming any
# one of them without also dropping (or narrowing) `implements TFile` is not
# a rename, it's a type error. Not renamed by W10 (out of scope -- W10's
# board was `Document`, `SyncableEntry.path`, and `connect`/`destroy` only).
TFILE_MIRROR_ADJUDICATED = {
    'AttachmentFile': frozenset({'name', 'extension', 'basename', 'stat', 'vault', 'parent'}),
}

# CLOSED (Mesh #6f9a8eb0, 2026-08-28): the "this vault entry belongs to a
# VaultShare" convention used to be spelled `sharedFolder` verbatim on
# `Document`, `TrackedFolder`, `TransferBatch`, `CanvasDocument`, and
# `AttachmentFile` alike -- all five renamed to `vaultShare` together
# (population C of that card; `RelaySettings.sharedFolders`, the top-level
# `data.json` key, is population A and deliberately untouched -- it is a
# wire name, not this convention). All five `sharedFolder` entries removed
# from the basket below; `_parent`/`s3rn`/`unsubscribes` stay, they were
# never part of this convention.
# (`_parent`/`vaultShare` name a `VaultShare`; the `parent` getter above
# names a `TFolder` -- a different concept that happens to share nearly the
# same word. That near-collision is real and worth a future pass, not this
# wave's.)
# Members a class only OVERRIDES -- the name is declared on a base class of
# ours, so the subclass cannot rename it in isolation and a polymorphic caller
# never sees the subclass's spelling anyway. W8 had a dict of this shape and
# emptied it in W9; W14 (Mesh #0b72373d) needs it again, for a much broader
# case than W8's single entry.
#
# MEASURED before adding: `destroy()` is DECLARED 64 times across src/. It is
# on `Notifier` (notifiers/Notifier.ts:84, reached by ShareRegistry through
# NotifierSet), on `ProviderBacked` (:413, reached by VaultShare), on the
# `SyncableEntry` and `Disposable` interfaces above, on `Clock`, and -- outside
# our tree entirely -- on Yjs's `Y.Doc.destroy()` and Svelte's `$destroy()`,
# both of which are called in the same files on adjacent lines. It is the
# codebase's single lifecycle verb, not vocabulary either of these two classes
# owns. Both base classes are themselves still in CLASS_RENAME_RESIDUE_DEFERRED,
# so the wave that renames the base renames every override with it, in one
# change that actually compiles.
#
# Keyed by DIRECT base, matching OWN_INTERFACE_ADJUDICATED's existing mechanism
# (_adjudicated_member reads `bases[cls]`, which is not transitive) rather than
# quietly making that lookup transitive for every basket at once.
OWN_BASE_CLASS_ADJUDICATED = {
    'Notifier': frozenset({'destroy'}),
    'NotifierSet': frozenset({'destroy'}),
    # W14: `VaultShare extends ProviderBacked` and overrides exactly these
    # four. `ProviderBacked` is W18's board (Mesh #a73c16d4's auth/credentials
    # wave), and an override cannot be renamed without its base: the base
    # declaration keeps the old spelling, every polymorphic caller goes through
    # the base type, and TypeScript rejects the subclass member outright.
    # Verified by reading both declarations rather than assuming --
    # ProviderBacked.ts:270 `connect()`, :99 `path?`, and its `intent` getter,
    # against VaultShare.ts:951/:156/:1129.
    #
    # Checked and NOT listed here: `destroyed` and `unsubscribes`. They look
    # like the same case (Notifier.ts:36-37 declares both), but VaultShare does
    # not descend from Notifier at all -- the chain is
    # VaultShare -> ProviderBacked -> Loggable, and Loggable extends nothing.
    # They are VaultShare's own fields that merely share a spelling with
    # another class's, so they were renamed (isTornDown / teardowns) rather
    # than excused. Worth stating explicitly: "a base class somewhere declares
    # this word" is not the test; "THIS class's base chain declares it" is.
    'ProviderBacked': frozenset({'destroy', 'connect', 'path', 'intent'}),
}

CONVENTION_ADJUDICATED = {
    'Document': frozenset({'_parent'}),
    'TrackedFolder': frozenset({'_parent'}),
    # `unsubscribes` is a SEPARATE convention, unrelated to the closed
    # sharedFolder->vaultShare rename: an `Unsubscriber[]`/teardown-callback
    # array field spelled `unsubscribes` verbatim across >= 10 unrelated
    # classes in this tree (VaultShare, TextViewPatch, FolderIndex,
    # ui/treeDecorations, ui/ExplorerDecorationCoordinator,
    # y-codemirror.next/LiveEditPlugin, notifiers/Notifier, ItemKinds,
    # featureToggleState, CanvasViewPatch, CanvasDocument) -- verified by grep,
    # not assumed from one prior sighting. Renaming CanvasDocument's copy alone
    # would fragment that same-purpose vocabulary from every sibling that
    # isn't in scope here, for a name upstream's own `Canvas` class also
    # happened to use (coincidence of a common pattern, not evidence upstream
    # invented the convention). A plugin-wide rename of all ~10 classes is its
    # own unit of work.
    'CanvasDocument': frozenset({'_parent', 'unsubscribes'}),
    #
    # `s3rn` is the ResourceAddress-identity convention, unrelated to the
    # closed sharedFolder->vaultShare rename -- shared verbatim across
    # `ProviderBacked`, `Document`, `VaultShare`, `CanvasDocument`, and
    # `AttachmentFile` (measured: `grep -rn '\bs3rn\b' src/` hits all five).
    # None of those other four are in this wave's board, and
    # `Document.ts`/`VaultShare.ts`/`CanvasDocument.ts` literally persist it
    # under the on-disk/IndexedDB key `"s3rn"` (a string literal, unaffected
    # by renaming the class MEMBER -- but renaming only AttachmentFile's copy
    # while the other four keep `s3rn` would leave one class speaking a
    # different word for the identical concept, exactly the half-migrated-
    # vocabulary state this wave's convention baskets exist to avoid).
    # Deferred here rather than renamed in isolation; a future wave doing
    # `ProviderBacked` (still in CLASS_RENAME_RESIDUE_DEFERRED below) is the
    # natural place to rename `s3rn` on all five classes together.
    # Wire-protocol half of `.s3rn` tracked separately at Mesh #f0e674e7.
    'AttachmentFile': frozenset({'_parent', 's3rn'}),
    #
    # W20 (Mesh #b8f7818d): Obsidian's `PluginSettingTab`/`SettingTab` base
# (obsidian.d.ts) documents its default `getControlValue`/`setControlValue`
# as reading/writing through `this.plugin` ("Reads from `this.plugin.settings`.
# Override to read from a different data source."), which means the running
# app's implementation conventionally sets/reads `this.plugin` on every
# `SettingTab` instance -- untyped in the .d.ts (no public `plugin` field is
# declared there), so a rename here produces zero compile signal either way.
# `RelaySettingsPage` doesn't currently call those two hooks, but renaming its
# own `plugin` field would decouple OUR copy from whatever the base class
# keeps calling `this.plugin` under the hood, with nothing to catch it if a
# future change (ours or Obsidian's) starts relying on that base behavior.
# W20 (Mesh #b8f7818d): `RelayOnPremShareClient.ts` declares its OWN, unrelated
# `interface Account` (a relay-onprem control-plane wire response: `id`,
# `email`, `name`, `is_admin`, `is_active`, `created_at`) that happens to share
# the class name `Account` with `src/Account.ts`'s renamed presence-account
# class. `collect()` accumulates members PER CLASS NAME across the whole
# tree, not per declaration/file, so once `src/Account.ts`'s own `id`/`email`/
# `name` fields were renamed away, the *interface*'s still-literal `id`/
# `email`/`name` kept the collision alive under the same `Account` key. Out of
# scope for this wave by design (see the task brief's own warning not to
# conflate the two) -- adjudicated by name, not via WIRE_SHAPE_TYPES, so this
# does not blanket-excuse every future member `src/Account.ts`'s own class
# might grow under the same name.
    'RelaySettingsPage': frozenset({'plugin'}),
    'Account': frozenset({'id', 'email', 'name'}),
    # W22 (Mesh #d61384ba): `ExplorerDecorationCoordinator` shares the
    # `unsubscribes` convention named above on `CanvasDocument` -- but
    # verified narrower than that entry's own "VaultShare, TextViewPatch, ...
    # CanvasViewPatch, CanvasDocument" list claims (that list predates this
    # wave and was carried forward uncritically once, which is exactly the
    # mistake this note corrects rather than repeats): `grep -rn '\bunsubscribes\s*[:=]'
    # src/` finds the field OWN-DECLARED (not merely inherited) on only
    # `CanvasDocument`, `FileUploadPill` (ui/treeDecorations.ts),
    # `LiveCMPluginValue` (y-codemirror.next/LiveEditPlugin.ts), this class,
    # and the `Notifier` base itself -- `TextViewPatch`/`CanvasViewPatch`
    # actually spell their equivalent field `unsubscribeFns`, a different
    # name, not a collision at all. `VaultShare`'s `ShareRegistry`,
    # `FolderIndex`, `ItemKinds`'s `KindRegistry`, and `featureToggleState`'s
    # class all merely USE `this.unsubscribes` -- inherited from `Notifier`,
    # not their own declaration, so renaming *their* usage doesn't touch this
    # class's word choice either way. What's still true and load-bearing: at
    # least 4 unrelated classes (CanvasDocument, FileUploadPill,
    # LiveCMPluginValue, this one) independently chose the identical spelling
    # for their own teardown-array field, which is the actual cross-cutting
    # convention -- renaming only this one copy would still fragment it from
    # the other 3. `ExplorerDecorationCoordinator`'s other 15 shared members
    # WERE renamed this wave (its class-wide entry removed from
    # CLASS_RENAME_RESIDUE_DEFERRED below), so `unsubscribes` needs its own
    # entry rather than riding that basket.
    'ExplorerDecorationCoordinator': frozenset({'unsubscribes'}),
    #
    # W-axis2-C (Mesh #0de35c1c). Implements the table from #df095a62 for the
    # Disposable/destroy family's non-rename lines. `destroy` itself is the
    # codebase's single lifecycle verb (measured in the adjudication task:
    # declared 64 times across src/, also Svelte's `$destroy()`, Yjs's
    # `Y.Doc.destroy()`, and two unrelated authorities -- `Disposable` above
    # and `ProviderBacked`/`Notifier` via OWN_BASE_CLASS_ADJUDICATED -- share
    # the same spelling), not vocabulary any ONE of these five classes owns:
    #   - BlobClient.destroy: unrelated to the (renamed) network methods on
    #     the same class; a plain field-nulling teardown, same shape as every
    #     other class below.
    #   - EmbeddedNoticeBar.destroy / ViewNoticeBar.destroy: both banner
    #     classes' cleanup method, verified NOT reached through Disposable
    #     (neither `implements Disposable` -- grep confirms) or any other
    #     registered base/interface; own-declared, generic teardown verb.
    #   - ExplorerTreeWalker.destroy: forwards to `item.destroy()` on the
    #     `Disposable`-typed decorations it stores (treeVisitor.ts's own
    #     interface) -- the walker's OWN method is not itself an
    #     implementor of that interface, so it doesn't ride
    #     OWN_INTERFACE_ADJUDICATED['Disposable']; it merely calls through it.
    #   - LazyValue.destroy: clears its pending-promise/timer state; the
    #     sibling `SingleFlight` class (asyncCache.ts) spells its own
    #     equivalent method identically, confirming this is the file's local
    #     convention rather than LazyValue-specific vocabulary.
    # `FileUploadPill.unsubscribes`: verified by grep to be the SAME
    # cross-cutting teardown-array convention already tracked above on
    # `CanvasDocument`/`ExplorerDecorationCoordinator` (>=4 unrelated classes
    # in this file alone independently spell their teardown-callback array
    # this way) -- not renamed in isolation for the same reason those two
    # entries give.
    # `PropertiesEditorSync.destroyed` / `ReadingViewSync.destroyed`: an
    # own-declared (not inherited) torn-down boolean flag, independently
    # chosen by both classes plus >=5 unrelated classes elsewhere in src/
    # (Notifier, LiveEditPlugin, RemoteSelections, LiveNodePlugin,
    # NotifierMap, SettingsPersistence per the wave-B registration above) --
    # generic lifecycle vocabulary, not upstream-specific. Their sibling
    # `render`/`destroy` members are OWN_INTERFACE (DocumentSurfaceSync,
    # above), NOT repeated here.
    'BlobClient': frozenset({'destroy'}),
    'EmbeddedNoticeBar': frozenset({'destroy'}),
    'ExplorerTreeWalker': frozenset({'destroy'}),
    'FileUploadPill': frozenset({'unsubscribes'}),
    'LazyValue': frozenset({'destroy'}),
    'ViewNoticeBar': frozenset({'destroy'}),
    'PropertiesEditorSync': frozenset({'destroyed'}),
    'ReadingViewSync': frozenset({'destroyed'}),
    # W-axis2-B (Mesh #d934b4b9). `Notifier.{_listeners, destroyed,
    # unsubscribes}` -- `destroy` itself is separately covered by
    # OWN_BASE_CLASS_ADJUDICATED['Notifier'] above, NOT repeated here; the
    # parent card explicitly warns not to assume `destroyed`/`unsubscribes`
    # ride along with that entry just because Notifier.ts:36-37 declares them
    # next to `destroy` -- checked each independently instead:
    #   - `unsubscribes`: verified by grep, this is the SAME cross-cutting
    #     teardown-array convention already tracked above on `CanvasDocument`/
    #     `ExplorerDecorationCoordinator` (>=4 unrelated classes independently
    #     spell their own teardown-callback array field this way) -- Notifier
    #     is simply the base declaration the other three inherit or echo, not
    #     a class-specific choice.
    #   - `destroyed`: verified by grep across src/, own-declared (not
    #     inherited) on Notifier plus PropertiesEditorSync, ReadingViewSync,
    #     LiveEditPlugin, RemoteSelections, LiveNodePlugin, NotifierMap (its
    #     own copy despite extending Notifier) and SettingsPersistence -- the
    #     same generic "torn-down" boolean flag chosen independently by at
    #     least 7 unrelated classes, not upstream-specific vocabulary.
    #   - `_listeners`: the ONE line here that is genuinely Notifier's own,
    #     not shared with any sibling (grep across src/ finds it declared
    #     nowhere else, `protected`, never read outside Notifier.ts itself).
    #     Kept CONVENTION rather than RENAME per the adjudication's own
    #     decision, not because it would be unsafe to rename in isolation --
    #     it is the base class's private storage for the interface members
    #     (`on`/`off`/`subscribe`/`dropSubscriber`) deferred above, and
    #     renaming the storage without revisiting the interface it backs
    #     would just be cosmetic churn on a base class already flagged as a
    #     future wave's work, not this one's.
    #   - `destroy`: bounced back by review (Mesh #d934b4b9) -- assumed
    #     covered by OWN_BASE_CLASS_ADJUDICATED['Notifier'] above (line
    #     ~1080) without reading `_adjudicated_member`'s actual mechanism
    #     first. That dict is keyed by a class's DIRECT BASE (`ifaces =
    #     bases.get(cls); base in ifaces`) -- it excuses `destroy` on
    #     classes whose base IS Notifier (NotifierSet, SettingsScope, ...),
    #     never on Notifier itself, since Notifier is not its own base.
    #     Measured against the axis-2 PREDECESSOR_TYPES basket (not main,
    #     which never counted these 6 lines to begin with): registering
    #     only `_listeners`/`destroyed`/`unsubscribes` left `Notifier.destroy`
    #     alone in the work basket (212 -> 207, not 206). Added here --
    #     same generic lifecycle verb as every sibling class's `destroy` in
    #     this same CONVENTION_ADJUDICATED dict, not a new judgment call.
    'Notifier': frozenset({'_listeners', 'destroy', 'destroyed', 'unsubscribes'}),
}

# Members that override a REAL method Obsidian's own base `Plugin` class
# declares (not just a name that happens to match upstream's custom `Live`
# class). `TeamRelayPlugin.removeCommand(command: string): void` shims the
# pre-1.7.2 Obsidian API gap (`requireApiVersion("1.7.2")` branches to
# `super.removeCommand(command)` on newer hosts, hand-rolls the removal via
# `app.commands`/`hotkeyManager` on older ones) -- it has to be spelled
# `removeCommand` to actually override `Plugin.prototype.removeCommand`
# (`node_modules/obsidian/obsidian.d.ts`), which is what lets every internal
# `this.removeCommand(...)` call site (and any future Obsidian-side caller)
# reach the shim uniformly. Renaming it away from the base-class name would
# not corrupt anything at runtime (nothing outside this file calls it), but
# it would silently stop being an override -- exactly the kind of footgun
# TFILE_MIRROR_ADJUDICATED exists to name for `Document`. Wave 15
# (#a73c16d4).
BASE_CLASS_OVERRIDE_ADJUDICATED = {
    'TeamRelayPlugin': frozenset({'removeCommand'}),
}


# OVERRIDE_CONTRACT_ADJUDICATED (Mesh #f34f11d3, closed 2026-08-28) used to
# hold `NotifierMap.unsubscribe`: an override of `Notifier.unsubscribe` (part
# of the `Subscribable<T>` interface, `src/notifiers/Notifier.ts`) whose base
# and third override link (`FilteredMap.unsubscribe`, same file) sat outside
# W21's board, so renaming only NotifierMap's copy would have silently broken
# the override -- any caller unsubscribing through a `Notifier`/
# `Subscribable`-typed reference would have skipped NotifierMap's
# derived-view ref-count teardown (`bumpDerivedRefCount`), with no compile
# error to flag it. Closed by renaming the whole chain in one motion:
# `Subscribable.unsubscribe` -> `dropSubscriber`, and the same rename on
# `Notifier`, `NotifierMap`, `FilteredMap`. Basket is empty; both it and this
# convention's check in `_adjudicated_member` are removed rather than kept
# empty, per the convention every ADJUDICATED basket in this file follows.
#
# The general convention (a member that is upstream vocabulary on its own
# class but ALSO overrides a same-named method on a base class outside the
# current wave's board) may recur on a future wave -- re-add a basket named
# for its own reason if it does, rather than reviving this one by name.


# ---------------------------------------------------------------------------
# Class-rename residue (Mesh #a2f4027a). Structural gap in the member axis
# above, distinct from every basket before this point: `shared_members` (in
# main(), below) only pairs (cls, member) when BOTH trees declare the SAME
# class name. Renaming a class -- something this epic has done to dozens of
# classes across 13 waves -- silently drops its entire member set out of
# that comparison, because the DICT KEY (the class name) stops matching, not
# because the members stopped being upstream's vocabulary. This was read
# throughout the epic as "renaming a type sweeps its members out for free"
# (wave-plan.py's own docstring says so) and used as a convenience; it
# actually means the members stopped being VISIBLE to the gate. W8 covered
# the mirror case -- class name UNCHANGED, so its members stay visible on
# their own merits (CONVERGENT_TYPES-driven exemption needed for `Document`/
# `Settings`/`ValidationError` specifically). This covers the case nothing
# had: class RENAMED, members untouched, invisible since the day the rename
# landed.
#
# PREDECESSOR_TYPES maps OUR current class name -> the upstream class name
# it replaced, so main() can additionally intersect our_members[ours]
# against up_members[predecessor] -- a second membership test the ordinary
# shared_members loop cannot express on its own, since that loop needs one
# key present in BOTH dicts and a renamed class is present in only one of
# them by definition.
#
# MEASURED, not recalled from memory or reconstructed from wave history: for
# every class in our tree with no upstream class of the same name, and every
# upstream class with no successor of the same name in ours, scored by RAW
# COUNT of shared non-generic member names -- not the ratio (Jaccard), which
# systematically UNDERCOUNTS a big upstream class absorbed into an even
# bigger one of ours. Worked example: `LoginManager` (28 members) ->
# `AuthSession` (45 members, only ~14 of them carried over from LoginManager,
# the rest grown independently across 13 waves) scores a LOW ratio (0.25)
# despite being a real, confirmed rename -- the denominator is diluted by
# our own unrelated growth, but the raw shared-member COUNT is exactly as
# real as a small class's. Tool: scripts/find-renamed-class-predecessors.py
# (a throwaway diagnostic, not the gate itself). Every entry below was
# independently confirmed by reading BOTH class declarations -- not trusted
# from the score alone, since a tiny shape-only interface (two unrelated
# 2-field DTOs both declaring `id`/`name`) can score a coincidental 1.0 with
# no rename relationship at all. Some low-count matches at the tail of the
# full scan (Modal subclasses sharing only `onOpen`/`onClose`/`plugin` --
# Obsidian's own lifecycle names, not upstream-specific vocabulary; generic
# storage interfaces sharing only `getData`/`setData`) were excluded on
# exactly this basis and are NOT in this table -- a further precision pass
# over that noisier tail is real remaining work, named rather than silently
# skipped (see the Mesh task's own closing comment for the cut line used).
# Axis-2 addendum (Mesh #f810d51d, 29.08.2026): 54 of the 66 residue pairs
# (class+INTERFACE successors alike -- the member axis's stack-based extract()
# never distinguished class/interface, so find-renamed-class-predecessors.py
# was never structurally blind to interfaces; the residue was simply that
# 13 prior waves happened to close classes first) were independently
# confirmed by reading both declarations, not by score. 12 residue
# candidates were rejected as coincidental -- shared vocabulary that is
# either an Obsidian Modal-lifecycle convention (onOpen/onClose/plugin) or
# a generic record/DTO shape (id/name/email, appId/path/relay) rather than
# upstream-specific wording, OR the upstream class already has a stronger,
# separately-confirmed successor (LoginManager->AuthSession,
# TenantConfig->TenantRecord, StoreAnalysis->ObjectStoreReport,
# ToastMessage->FlashMessage) that the coincidental match would have
# duplicated. Two entries (OperationBase, and originally SettingsBackend +
# SettingsBackendBase) corrected the diagnostic tool's top-ranked candidate:
# both had MULTIPLE upstream classes tied at the same (shared-count, score)
# -- find-renamed-class-predecessors.py's tie-break falls through to Python
# `set` iteration order, which is not deterministic run-to-run under hash
# randomization -- and the semantically correct match (the upstream BASE
# interface each tied variant/implementer itself derives from: `Operation`,
# not one variant `Upgrade`; `ISettingsStorage`, not one implementer
# `ObsidianSettingsStorage`) had to be picked by reading, same as any other
# entry. Full per-pair reasoning (all 66, both directions): Mesh #f810d51d.
# SettingsBackend/SettingsBackendBase/VaultSettingsBackend/
# InMemorySettingsBackend (and their PREDECESSOR_TYPES + adjudication
# entries) were later deleted outright as dead code -- Mesh #f3902463, zero
# callers anywhere outside their own declaration file, confirmed by grep
# and by the production bundle: not literally byte-identical (removing the
# declarations shifts esbuild's minified LOCAL BINDING numbering globally,
# same caveat as #2ee0effc/sol-bundle-proof-differs-for-module-vs-member-
# deletion), but the set of preserved (>=8-char) identifiers -- the thing
# that actually distinguishes shipped content from renumbering noise -- is
# IDENTICAL before and after (0 lost, 0 gained), and InMemorySettingsBackend's
# own distinguishing field name (`storedValue`) is present in NEITHER bundle,
# confirming this code was already tree-shaken out before the source deletion.
PREDECESSOR_TYPES = {
    'Account': 'User',
    'ActionLineArgs': 'ActionLine',
    'AttachmentCategory': 'SyncCategory',
    'AttachmentFile': 'SyncFile',
    'AttachmentRecordBase': 'BaseFileMeta',
    'AttachmentSyncSettings': 'SyncSettingsManager',
    'AttachmentToggles': 'SyncFlags',
    'AttachmentTypeSpec': 'TypeSettings',
    'AuthSession': 'LoginManager',
    'AuthSettings': 'LoginSettings',
    'AwarenessUser': 'AwarenessUserData',
    'BlobClient': 'ContentAddressedStore',
    'CanvasAddress': 'S3Canvas',
    'CanvasDocument': 'Canvas',
    'CanvasViewBinding': 'RelayCanvasView',
    'CanvasViewPatch': 'CanvasPlugin',
    'Clock': 'TimeProvider',
    'CollaboratorPresence': 'AwarenessUserData',
    'CredentialCache': 'TokenStore',
    'CredentialCacheOptions': 'TokenStoreConfig',
    'CredentialEntry': 'TokenInfo',
    'Delivery': 'Mail',
    'DiffHunk': 'Difference',
    'DiffViewState': 'ViewState',
    'DocumentAddress': 'S3Document',
    'DocumentGrant': 'ClientToken',
    'DocumentViewBinding': 'LiveView',
    'EmbeddedNoticeBar': 'EmbedBanner',
    'ExplorerDecorationCoordinator': 'FolderNavigationDecorations',
    'ExplorerTreeWalker': 'FileExplorerWalker',
    'ExternalLinkPluginValue': 'InvalidLinkPluginValue',
    'FeatureToggleState': 'FeatureFlagManager',
    'FileAddress': 'S3File',
    'FileDiffResult': 'FileDifferences',
    'FileDiffView': 'DifferencesView',
    'FileGrant': 'FileToken',
    'FileHashCache': 'ContentAddressedFileStore',
    'FileHashEntry': 'FileCacheEntry',
    'FileRecord': 'FileInfo',
    'FileUploadPill': 'FilePillDecoration',
    'FlashMessage': 'ToastMessage',
    'FolderIndex': 'SyncStore',
    'FolderLiveIndicator': 'FolderBar',
    'FolderMembership': 'FolderRole',
    'FolderPickerOption': 'FolderSuggestion',
    'HashedFile': 'ContentAddressedFile',
    'HostCanvas': 'ObsidianCanvas',
    'HostCanvasEdge': 'CanvasEdge',
    'HostCanvasNode': 'CanvasNode',
    'HostCanvasView': 'CanvasView',
    'HunkActionBar': 'ActionLine',
    'HunkActionButton': 'ActionLineButton',
    'ItemRecordBase': 'MetaBase',
    'KindRegistry': 'TypeRegistry',
    'KindSupport': 'ProtocolSupport',
    'LazyValue': 'Dependency',
    'LicenseClaims': 'EndpointJWTPayload',
    'LicenseRecord': 'License',
    'LicenseSummary': 'LicenseInfo',
    'LogFileAdapter': 'ObsidianFileAdapter',
    'LogWriterConfig': 'LogConfig',
    'NavView': 'View',
    'NotificationDispatcher': 'PostOffice',
    'Notifier': 'Observable',
    'NotifierMap': 'ObservableMap',
    'NotifierSet': 'ObservableSet',
    'ObjectStoreReport': 'StoreAnalysis',
    'OperationBase': 'Operation',
    'PatchRegistry': 'Patcher',
    'PathPatch': 'View',
    'PresenceTitleDecorator': 'AwarenessViewPlugin',
    'PropertiesEditorSync': 'PreviewRenderer',
    'ProtocolLinkParams': 'Parameters',
    'ProviderBacked': 'HasProvider',
    'ReadingViewSync': 'PreviewRenderer',
    'RelayCredentialCache': 'LiveTokenStore',
    'RelayOnPremAuthStore': 'LocalAuthStore',
    'RelayRegistry': 'RelayManager',
    'RelaySettingsPage': 'LiveSettingsTab',
    'RelayWorkspace': 'Relay',
    'RemoteCanvasAddress': 'S3RemoteCanvas',
    'RemoteDocumentAddress': 'S3RemoteDocument',
    'RemoteFileAddress': 'S3RemoteFile',
    'RemoteFolderAddress': 'S3RemoteFolder',
    'RemoteFolderRecord': 'RemoteSharedFolder',
    'RenameOp': 'Rename',
    'ResourceAddress': 'S3RN',
    'ServiceHealthMonitor': 'NetworkStatus',
    'ServiceHealthReport': 'ServiceStatus',
    'SettingsScope': 'NamespacedSettings',
    'ShareRegistry': 'SharedFolders',
    'SignedOutViewBinding': 'LoggedOutView',
    'SigningAuthority': 'ProviderAuto',
    'StorageAllocation': 'StorageQuota',
    'StorageUsageSummary': 'DBSummaryStats',
    'SuggestPickerModal': 'GenericSuggestModal',
    'SyncOpBase': 'Operation',
    'SyncQueueIndicator': 'QueueWatcher',
    'SyncableEntry': 'IFile',
    'SystemClock': 'TimeProvider',
    'TeamRelayPlugin': 'Live',
    'TenantConfigModal': 'EndpointConfigModal',
    'TenantRecord': 'TenantConfig',
    'TenantRegistry': 'EndpointManager',
    'TenantSettings': 'EndpointSettings',
    'TextViewPatch': 'TextFileViewPlugin',
    'TrackedFolder': 'SyncFolder',
    'TrackedLink': 'CacheLink',
    'TransferBatch': 'SyncGroup',
    'TransferProgress': 'SyncProgress',
    'TransferQueue': 'BackgroundSync',
    'TransferTask': 'QueueItem',
    'UnsavedFile': 'DiskBuffer',
    'UnsavedFileStore': 'DiskBufferStore',
    'VaultFileSink': 'ObsidianFileAdapter',
    'VaultScopedMap': 'LocalStorage',
    'VaultShare': 'SharedFolder',
    'VaultShareSettings': 'SharedFolderSettings',
    'ViewBinding': 'S3View',
    'ViewBindingRegistry': 'LiveViewManager',
    'ViewNoticeBar': 'Banner',
    'ViewSurfaceBridge': 'ViewHookPlugin',
    'WorkspaceInvitation': 'RelayInvitation',
    'WorkspaceMembership': 'RelayRole',
    'WorkspaceSubscription': 'RelaySubscription',
    'WorkspaceUser': 'RelayUser',
}

# Of the 74 classes in PREDECESSOR_TYPES above, 64 still had members left
# over after the ordinary contract/generic/convergent classification (i.e.
# real, specific upstream vocabulary -- not just a coincidentally-shared
# framework or storage-interface verb) when this basket was built. Renaming
# those classes' members safely means the SAME per-call-site tracing every
# gate-4 wave has always needed (a member name can collide with an unrelated
# method on a different type, a third-party API the class wraps, a
# wire-protocol field, ...) -- just at a scale (`VaultShare` alone carries
# 100, `TeamRelayPlugin` 49, `ViewBindingRegistry`/`TransferQueue` 38 each)
# that is its own multi-wave epic on the scale of the ENTIRE prior 13-wave
# gate-4 initiative combined, not a rider on the card that found this gap.
# Deferred here at CLASS granularity rather than per-member (the ADJUDICATED
# convention used everywhere else in this file): at this volume, listing
# every individual (class, member) pair with its own reason would be a
# multi-thousand-line dict that is no more legible than the class list
# below, and the full per-member breakdown is already measured and attached
# to the tracking task rather than duplicated into a giant comment here.
#
# W21 (Mesh #61c5c11a) closed 6 of the 64: `NotifierMap`, `NotifierSet`,
# `NotificationDispatcher`, `PatchRegistry`, `Clock`, `SystemClock` -- all 64
# of their combined members renamed except `NotifierMap.unsubscribe`, left
# adjudicated at the time (the now-removed OVERRIDE_CONTRACT_ADJUDICATED
# basket, above) because its override chain reached `Notifier`/`Subscribable`
# and `FilteredMap.unsubscribe`, outside W21's board. Mesh #f34f11d3 closed
# that deferral by renaming the whole chain together.
#
# W22 (Mesh #d61384ba) closes the 8 that were actually enumerated in this
# set: `ExplorerDecorationCoordinator`, `ExternalLinkPluginValue`,
# `PresenceTitleDecorator`, `SuggestPickerModal`, `ServiceHealthMonitor`,
# `KindRegistry`, `ObjectStoreReport`, `SyncableEntry` -- 60 of their combined
# members actually renamed this wave (`constructor`/`update`+`destroy`-on-a-
# `PluginValue`/`onOpen`/`onClose` already resolve to `contract` once a class
# leaves this basket, so needed no rename at all; `SyncableEntry`'s
# `guid`/`disconnect` and `ExplorerDecorationCoordinator`'s `unsubscribes`
# needed their own `CONVENTION_ADJUDICATED` entries instead -- see there for
# why, and Mesh #fe4e6843 for the follow-up that closes the former). The set
# is now empty: the much larger PREDECESSOR_TYPES-derived backlog this
# comment block's own history describes was never fully enumerated as
# literal entries here (measured, not enumerated, per the block above) --
# whatever of it resurfaces as `work` on a future `check-naming.sh` run gets
# examined and re-added by name then, the same way every entry above was.
#
# NOT permanent, same as every other ADJUDICATED-style basket: a future wave
# removes a class from this set once its member residue is actually renamed
# (or explicitly re-adjudicated by name into one of the baskets above, for
# whichever members turn out to need their own contract/generic reasoning).
CLASS_RENAME_RESIDUE_DEFERRED = frozenset({
})


def _adjudicated_member(cls, name, bases):
    if not cls:
        return False
    if cls in CLASS_RENAME_RESIDUE_DEFERRED:
        return True
    ifaces = (bases or {}).get(cls, ())
    for iface, members in OWN_INTERFACE_ADJUDICATED.items():
        if iface in ifaces and name in members:
            return True
    for base, members in OWN_BASE_CLASS_ADJUDICATED.items():
        if base in ifaces and name in members:
            return True
    if name in TFILE_MIRROR_ADJUDICATED.get(cls, ()):
        return True
    if name in CONVENTION_ADJUDICATED.get(cls, ()):
        return True
    if name in BASE_CLASS_OVERRIDE_ADJUDICATED.get(cls, ()):
        return True
    return False


def basket_file(rel):
    # By name only. VENDOR_DIRS is deliberately NOT consulted here: a directory
    # prefix would annex any file dropped under `client/` tomorrow as contract,
    # with no by-name justification -- the exact hole this gate's docstring
    # disclaims, and it was live in the first draft. Every real source file in
    # those directories is already enumerated in VENDOR_FILES, so the prefix
    # bought nothing and risked everything. VENDOR_DIRS survives only on the
    # `dir` axis, where a directory HAS no by-name alternative.
    return 'contract' if rel in VENDOR_FILES else 'work'


def basket_name(name, kind, where, cls=None, bases=None, zero_arg=None):
    """Contract only where an external authority actually fixes THIS name on
    THIS declaration. Matching on spelling alone is what made the first draft
    report greener than the truth."""
    if kind == 'type':
        if name in CONTRACT_TYPES:
            return 'contract'
        return 'convergent' if name in CONVERGENT_TYPES else 'work'
    if kind == 'export' and name in CONVERGENT_EXPORTS:
        return 'convergent'
    if kind == 'export' and name in CONVERGENT_TYPE_GUARD_EXPORTS:
        return 'convergent'
    # Every rule below is about a name ON A CLASS. A module-level export that
    # merely shares the spelling is not the thing: Obsidian calls methods on
    # objects, and a Svelte store is an object. `getSuggestions` in
    # components/GenericSuggest.svelte is an ordinary component prop
    # (`export let getSuggestions: (query: string) => any[] = () => []`), has
    # nothing to do with AbstractInputSuggest.getSuggestions, and is ours to
    # rename -- it sat in the contract basket because this branch used to
    # return early for every non-member kind.
    if kind != 'member':
        return 'work'
    if _adjudicated_member(cls, name, bases):
        return 'adjudicated'
    if cls and cls in STRUCTURAL_EXTERNAL_TYPES:
        return 'contract'
    if _declared_interface_contract(cls, name, bases):
        return 'contract'
    if name in LANG_PROTOCOLS:
        return 'contract'
    if name in SVELTE_LIFECYCLE and where.endswith('.svelte'):
        return 'contract'
    if name in SVELTE_STORE_MEMBERS:
        # the run callback IS the contract; a zero-arg `subscribe()` is not it
        if cls and zero_arg and name in zero_arg.get(cls, ()):
            return 'work'
        return 'contract'
    if name in CM_PLUGIN_MEMBERS:
        return 'contract' if cls and _is_cm_plugin_value(cls) else 'work'
    if name in OBSIDIAN_HOOKS:
        return ('contract'
                if cls and _reaches_obsidian_base(cls, bases or {})
                else 'work')
    if cls and cls in WIRE_SHAPE_TYPES:
        return 'contract'
    return 'work'


def main():
    args = list(sys.argv[1:])
    cap, samples_to, out_json, limit = None, None, None, 40
    for flag in ('--max-work', '--show-samples', '--json', '--limit'):
        while flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"FATAL: {flag} needs a value", file=sys.stderr)
                return 2
            val = args[i + 1]
            del args[i:i + 2]
            if flag == '--max-work':
                cap = int(val)
            elif flag == '--show-samples':
                samples_to = val
            elif flag == '--limit':
                limit = int(val)
            else:
                out_json = val
    if len(args) < 2:
        print(__doc__)
        return 2
    up_root, our_root = args[0], args[1]
    for r in (up_root, our_root):
        if not os.path.isdir(r):
            print(f"FATAL: not a directory: {r}", file=sys.stderr)
            return 2

    up_files, up_dirs = walk_tree(up_root)
    our_files, our_dirs = walk_tree(our_root)
    if not up_files or not our_files:
        print("FATAL: one of the trees has no source files", file=sys.stderr)
        return 2

    shared_files = sorted(up_files & our_files)
    shared_dirs = sorted(up_dirs & our_dirs)

    up_types, up_exports, up_members, _, _ = collect(up_root, up_files)
    (our_types, our_exports, our_members,
     our_bases, our_zero_arg) = collect(our_root, our_files)

    shared_types = sorted(set(up_types) & set(our_types))
    shared_exports = sorted(set(up_exports) & set(our_exports))
    shared_members = []
    for cls in sorted(set(up_members) & set(our_members)):
        for name in sorted(set(up_members[cls]) & set(our_members[cls])):
            shared_members.append((cls, name,
                                   sorted(our_members[cls][name])[0]))
    # Class-rename residue (Mesh #a2f4027a, PREDECESSOR_TYPES above): the loop
    # above requires the SAME class name in both dicts, which a renamed class
    # can never satisfy. Compare OUR renamed class's members against its
    # PREDECESSOR's members instead -- a different key in up_members than the
    # one `cls` names, which is exactly what the ordinary loop cannot express.
    for ours, predecessor in sorted(PREDECESSOR_TYPES.items()):
        if ours not in our_members or predecessor not in up_members:
            continue
        for name in sorted(set(up_members[predecessor]) & set(our_members[ours])):
            shared_members.append((ours, name,
                                   sorted(our_members[ours][name])[0]))

    rows = []
    for rel in shared_files:
        b = basket_file(rel)
        if b == 'work' and (rel in CONVERGENT_FILES or rel in PLATFORM_CONVENTION_FILES):
            b = 'convergent'
        rows.append({'axis': 'file', 'name': rel, 'where': rel, 'basket': b})
    for d in shared_dirs:
        rows.append({'axis': 'dir', 'name': d, 'where': d,
                     'basket': 'contract' if d.split('/')[0] in VENDOR_DIRS
                     else 'convergent' if d in CONVERGENT_DIRS
                     else 'work'})
    for n in shared_types:
        where = our_types[n]
        rows.append({'axis': 'type', 'name': n, 'where': where,
                     'basket': 'contract' if basket_file(where) == 'contract'
                     else basket_name(n, 'type', where)})
    for n in shared_exports:
        where = our_exports[n]
        rows.append({'axis': 'export', 'name': n, 'where': where,
                     'basket': 'contract' if basket_file(where) == 'contract'
                     else basket_name(n, 'export', where, None, our_bases, our_zero_arg)})
    for cls, n, where in shared_members:
        rows.append({'axis': 'member', 'name': f'{cls}.{n}', 'where': where,
                     'basket': 'contract' if basket_file(where) == 'contract'
                     else basket_name(n, 'member', where, cls, our_bases, our_zero_arg)})

    print(f"upstream src files: {len(up_files):4d}   ours: {len(our_files):4d}")
    print()
    print(f"{'axis':8s} {'shared':>7s} {'contract':>9s} {'converged':>10s} "
          f"{'adjudicat':>10s} {'work':>7s}")
    order = ('file', 'dir', 'type', 'member', 'export')
    for axis in order:
        sel = [r for r in rows if r['axis'] == axis]
        w = sum(1 for r in sel if r['basket'] == 'work')
        cv = sum(1 for r in sel if r['basket'] == 'convergent')
        adj = sum(1 for r in sel if r['basket'] == 'adjudicated')
        print(f"{axis:8s} {len(sel):7d} {len(sel) - w - cv - adj:9d} "
              f"{cv:10d} {adj:10d} {w:7d}")
    work = [r for r in rows if r['basket'] == 'work']
    contract = [r for r in rows if r['basket'] == 'contract']
    convergent = [r for r in rows if r['basket'] == 'convergent']
    adjudicated = [r for r in rows if r['basket'] == 'adjudicated']
    print(f"{'TOTAL':8s} {len(rows):7d} {len(contract):9d} "
          f"{len(convergent):10d} {len(adjudicated):10d} {len(work):7d}")

    print(f"\nwork basket: {len(work)} shared names across "
          f"{len({r['where'] for r in work})} files")
    by_axis = defaultdict(list)
    for r in work:
        by_axis[r['axis']].append(r)
    for axis in order:
        sel = by_axis.get(axis, [])
        if not sel:
            continue
        print(f"\n-- {axis} ({len(sel)}) " + "-" * 40)
        for r in sel[:limit]:
            print(f"   {r['name']}"
                  + ("" if r['axis'] in ('file', 'dir')
                     else f"   [{r['where']}]"))
        if len(sel) > limit:
            print(f"   ... {len(sel) - limit} more (--limit N to see them)")

    if adjudicated:
        print(f"\nadjudicated basket: {len(adjudicated)} shared names named "
              f"and reasoned in this script (not work, not contract)")
        for r in sorted(adjudicated, key=lambda r: r['name']):
            print(f"   {r['name']}   [{r['where']}]")

    if samples_to:
        with open(samples_to, 'w', encoding='utf-8') as fh:
            for r in sorted(rows, key=lambda r: (r['axis'], r['name'])):
                fh.write(f"{r['basket']}\t{r['axis']}\t{r['name']}\t"
                         f"{r['where']}\n")
        print(f"\nfull classified list -> {samples_to}")
    if out_json:
        with open(out_json, 'w', encoding='utf-8') as fh:
            json.dump({'upstream_files': len(up_files),
                       'our_files': len(our_files),
                       'rows': rows,
                       'work': len(work), 'contract': len(contract),
                       'adjudicated': len(adjudicated)},
                      fh, indent=1)
        print(f"json -> {out_json}")

    if cap is not None and len(work) > cap:
        print(f"\nFAIL: work basket {len(work)} > --max-work {cap}")
        return 1
    if cap is not None:
        print(f"\nOK: work basket {len(work)} <= --max-work {cap}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
