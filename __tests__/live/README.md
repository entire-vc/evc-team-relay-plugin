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

## Bringing the stack up

The harness needs a running Team Relay stack: postgres, minio, control-plane and
relay-server. Its compose file is not in this repository — it is
`infra/docker-compose.yml` in the `evc-team-relay` repository. That file is
production-shaped: relay-server only exposes its ports inside the compose
network, and nothing is published to the host. `docker-compose.live.yml`, next to
this README, is the override that makes it usable from a test client on the
host. It:

- publishes the ports the harness defaults point at, on `127.0.0.1` only;
- sets `RELAY_PUBLIC_URL` and `RELAY_AUDIENCE` for the local stack (see
  [the audience section](#stack-requirement-the-cwt-audience-must-match));
- starts only the four services the harness talks to (plus the one-shot
  `minio-init` and `control-plane-migrate`), leaving out caddy, the workers,
  prometheus, grafana and web-publish — the last one cannot be built without a
  token for private packages, and caddy would publish ports 80 and 443;
- sets `CONTROL_PLANE_PUBLIC_URL` to `http://localhost:58080`, the base URL the
  control-plane hands out for file uploads and downloads;
- keeps all state in named volumes, so `down -v` removes everything and two
  projects never share MinIO data.

| host port | service | container port |
|---|---|---|
| 58080 | control-plane | 8000 |
| 58081 | relay-server | 8080 |
| 59000 | minio | 9000 |
| 55432 | postgres | 5432 |

**Use a separate checkout of `evc-team-relay` for this**, not one that holds a real
install: the setup below writes `infra/.env` and `infra/relay/relay.toml` in it.
Both are git-ignored, and a copy without git history is enough:

```bash
git clone --depth 1 <evc-team-relay remote> ~/trlive-base
# or, without git history:  mkdir -p ~/trlive-base && git archive HEAD | tar -x -C ~/trlive-base
cd ~/trlive-base/infra
```

One-time setup — a keypair, an `.env` and a `relay.toml` whose `[server].url`
equals `RELAY_AUDIENCE` from the override. This needs **OpenSSL 3**: the system
`openssl` on macOS is LibreSSL and has no `ed25519` (`brew install openssl@3` and
put it first in `PATH`). The guards below stop on that instead of leaving
`RELAY_PRIVATE_KEY` empty, which the control-plane refuses to start with. Run the
block as a script (`bash setup.sh`), not pasted into an interactive shell: a
failed guard calls `exit`.

```bash
openssl genpkey -algorithm ed25519 -out relay_private.pem || exit 1
PRIV=$(openssl base64 -A -in relay_private.pem)
[ -n "$PRIV" ] || { echo "no private key generated"; exit 1; }
# The raw 32-byte public key is the tail of the DER-encoded SubjectPublicKeyInfo.
PUB=$(openssl pkey -in relay_private.pem -pubout -outform DER | tail -c 32 | openssl base64 -A)
rm relay_private.pem

cp env.example .env
sed -i.bak "s|^RELAY_PRIVATE_KEY=.*|RELAY_PRIVATE_KEY=$PRIV|; s|^JWT_SECRET=.*|JWT_SECRET=$(openssl rand -hex 32)|" .env

cp relay/relay.toml.example relay/relay.toml
sed -i.bak \
  -e 's|^url = .*|url = "http://localhost:58080"|' \
  -e 's|key_id = "REPLACE_WITH_KEY_ID"|key_id = "relay_cp_dev"|' \
  -e "s|public_key = \"REPLACE_WITH_PUBLIC_KEY_BASE64\"|public_key = \"$PUB\"|" \
  -e 's|access_key = "MINIO_ROOT_USER"|access_key = "relay"|' \
  -e 's|secret_key = "MINIO_ROOT_PASSWORD"|secret_key = "change-this-too"|' \
  relay/relay.toml
rm -f .env.bak relay/relay.toml.bak
```

`env.example` already carries the bootstrap admin the harness logs in as
(`admin@example.com` / `super-secret-pass`, the `LIVE_ADMIN_*` defaults below).

Bring it up, **rebuilding the images from the checkout** — run from this
repository's root, with `BASE` pointing at the checkout's `infra/` directory:

```bash
BASE=~/trlive-base/infra
docker compose -p trlive \
  -f "$BASE/docker-compose.yml" \
  -f __tests__/live/docker-compose.live.yml \
  up -d --build
```

Check that it is healthy by looking at the response body, not only the status
code — an error page can be a 200:

```bash
curl -s http://localhost:58080/health          # {"ok":true}
curl -s http://localhost:58080/health/ready    # database-checked readiness
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:58081/ready   # relay-server: 200
```

Stop it and delete its state:

```bash
docker compose -p trlive -f "$BASE/docker-compose.yml" -f __tests__/live/docker-compose.live.yml down -v
```

Always pass **both** `-f` files, and use the same pair every time. Recreating a
container from the base file alone silently drops the port mappings and
`RELAY_AUDIENCE`: `localhost:58081/ready` then refuses connections while
`docker compose ps` still shows everything healthy. `docker compose ls -a` prints
the files an existing project was created with.

The first `--build` is slow: relay-server compiles a Rust workspace from source,
roughly ten minutes on a laptop. Later runs reuse the build cache; after changing
control-plane or relay-server code, rerun the same `up -d --build` and only the
changed images are rebuilt and recreated.

**Do not run this on a Docker host that also runs a real Team Relay install.**
Named volumes are isolated per project, but the base file pins the image tags
`infra-control-plane:latest` and `infra-relay-server:latest`, which are shared
across projects: `up --build` retags them, and the real install's next recreate
would start the test build.

## Environment

Defaults match the local docker stack above (`docker compose -p trlive`):

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
`RELAY_PUBLIC_URL` (its host and port, forced to `https://`) unless
`RELAY_AUDIENCE` is set explicitly.

If they disagree, **every** connection is refused and the only visible symptom is
a websocket that never opens. The relay-server names it plainly in its log:

```
WARN y_sweet_core::cwt: CWT audience validation failed - token intended for
     different service expected="http://localhost:58080" found="https://example.com"
```

For the local stack that means the control-plane needs the following (set for you
by `docker-compose.live.yml`, together with a `relay.toml` whose `[server].url` is
`http://localhost:58080`):

```yaml
RELAY_PUBLIC_URL: "ws://localhost:58081"   # reachable relay-server, client-facing
RELAY_AUDIENCE:   "http://localhost:58080" # must equal relay.toml [server].url exactly
```

`infra/env.example`'s shipped `RELAY_PUBLIC_URL=wss://${DOMAIN_BASE}` produces
`aud=https://example.com`, which does not match, and additionally points clients
at a host that does not resolve. Even without the shipped value, leaving
`RELAY_AUDIENCE` unset would derive `https://localhost:58081` from the local
`RELAY_PUBLIC_URL`, which is not `http://localhost:58080` either.

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
