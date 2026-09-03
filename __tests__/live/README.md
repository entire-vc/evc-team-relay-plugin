# LIVE relay harness

Runs the rewritten sync core against a **real** relay stack — no mocked relay,
no mocked websocket, no mocked tokens, no mocked HTTP.

```bash
LIVE_RELAY=1 npx jest --config jest.live.config.js
```

It is **excluded from `npm test`** (`jest.config.js` ignores `__tests__/live/`),
so the hermetic suite stays at its 40-suite / 453-test baseline and never depends
on a server being up.

## What it covers

| Step | Covered | How |
|---|---|---|
| 1. Token chain | yes | real password login → real `POST /tokens/relay` → relay-server accepts the CWT on a real websocket |
| 2. Two-client convergence | yes | two independent `Y.Doc`s through `ProviderBacked` → `client/provider.ts`, asserted on **text content** both directions |
| 3. Persistence across reconnect | yes | writer + witness prove the server holds the text, both disconnect, a fresh client re-reads it; asserts the pre-sync read is empty and the post-sync read is not |
| 3b. Durability past server eviction | yes | all clients leave, the relay's own log is polled until it reports `Terminating loop for <doc>`, then a new client re-reads the text — served from MinIO, not a warm room |
| 4. Folder path through `VaultShare.ts` | no | share create/read-back via `RelayOnPremShareClient` is covered; `VaultShare` itself needs a real Obsidian `Vault`/`FileManager`/`App` — see below |

## Environment

Defaults match the local docker stack (`docker compose -p trlive`):

| var | default |
|---|---|
| `LIVE_RELAY` | *(required)* set to `1` |
| `LIVE_CONTROL_PLANE` | `http://localhost:58080` |
| `LIVE_RELAY_SERVER` | `http://localhost:58081` |
| `LIVE_ADMIN_EMAIL` | `admin@example.com` |
| `LIVE_ADMIN_PASSWORD` | `super-secret-pass` |
| `LIVE_RELAY_LOG_CMD` | `docker compose -p trlive logs relay-server --since 5m` |
| `LIVE_SKIP_EVICTION` | unset; `1` skips the ~40s durability test |

The suite fails loudly in `beforeAll` if either service is not answering, rather
than producing a confusing mid-test websocket error.

## Stack requirement: the CWT audience must match

The relay-server validates the `aud` claim on every token against its own
`relay.toml` `[server].url`. The control-plane derives that claim from
`RELAY_PUBLIC_URL` (host only, forced to `https://`) unless `RELAY_AUDIENCE` is
set explicitly.

If they disagree, **every** connection is refused and the only visible symptom is
a websocket that never opens. The relay-server names it plainly in its log:

```
WARN y_sweet_core::cwt: CWT audience validation failed - token intended for
     different service expected="http://localhost:58080" found="https://example.com"
```

For the local stack that means the control-plane needs:

```yaml
RELAY_PUBLIC_URL: "ws://localhost:58081"   # reachable relay-server, client-facing
RELAY_AUDIENCE:   "http://localhost:58080" # must equal relay.toml [server].url exactly
```

`infra/.env`'s shipped `RELAY_PUBLIC_URL=wss://${DOMAIN_BASE}/doc/ws` produces
`aud=https://example.com`, which does not match, and additionally points clients
at a host that does not resolve.

## What is mocked, and why that is allowed

Only `obsidian` — mapped by `jest.live.config.js` to `__tests__/live/obsidianLive.ts`.
That module re-exports the shared unit-test mock for the inert bits (`TFile`,
`Notice`, `debounce`, …) and implements `requestUrl` over Node's real `fetch`, so
`src/customFetch.ts` and everything above it issue genuine HTTP.

The Obsidian app API is a true external boundary per the repo's mocking
convention; the relay, the tokens and the CRDT traffic are not, and none of them
are stubbed here.

`ProviderBacked` also takes a `AuthSession`. The harness passes an object carrying
a real `Account` built from the real authenticated identity, because `.user` (for
awareness seeding) is the only member `ProviderBacked` reads, and the relay-onprem
token path ignores `AuthSession` entirely
(`RelayCredentialRefresh.refreshRelayOnPrem`). Constructing the real
`AuthSession` would pull in `TenantRegistry`, `SettingsScope` and the
PocketBase adapter, none of which participate in this path.

## Why step 4 stops where it does

`VaultShare`'s constructor takes twelve collaborators — `Vault`, `FileManager`,
`App`, `RelayRegistry`, `FileHashCache`, `TransferQueue`,
`SettingsScope`, … Driving it headlessly would mean standing in for
`RelayRegistry` and `TransferQueue`, which are themselves part of the rewritten
core: mocking them would defeat the purpose of this harness. Folder-level
coverage needs a real vault (an Obsidian test vault or an e2e harness), not more
test doubles.
