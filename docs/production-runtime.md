# GoreeCloud Notify production runtime and private-publication readiness

## Purpose

I use this document to define the source-controlled production runtime contract for GoreeCloud Notify before any target-host deployment or `notify.goreecloud.com` cutover is approved.

This repository state is **production-readiness evidence, not production deployment**. ntfy remains the active production notification service until the separate target-environment, monitoring, recovery, producer-migration, and rollback gates are completed.

## Runtime design

I use one final GoreeCloud Notify application container in production.

The production image is built in two stages:

1. the pinned Node build stage installs the committed frontend lock with `npm ci` and compiles immutable Vite assets;
2. the pinned Python runtime stage contains FastAPI, Alembic, backend code, and the compiled frontend artifact.

The Node build toolchain is not present in the final runtime image. FastAPI serves the generated frontend index and hashed static assets from the same application origin as the API.

This keeps the private publication path simple:

```text
Approved NetBird client
        |
        v
AdGuard Home private DNS
notify.goreecloud.com
        |
        v
Central GoreeCloud Caddy HTTPS
        |
        v
external Docker proxy network
        |
        v
goreecloud-notify:8000
```

I do not publish port 8000 to the production host. Caddy reaches the application by container identity over the approved external `proxy` network.

## Frontend serving and caching

The browser uses same-origin API paths in production. `VITE_API_BASE_URL` remains available for the separate development topology but is not required by the production build.

The production runtime applies these cache boundaries:

- `/` is served with `Cache-Control: no-store` so the application shell is not retained across deployments;
- Vite-generated `/assets/*` resources are served with a one-year immutable cache directive because their filenames are content-hashed;
- API responses are not routed through the immutable static-asset handler.

## Container security boundary

`docker-compose.production.yml` preserves the least-privilege controls already established by GoreeCloud Notify development and makes them explicit for the production contract:

- runtime UID/GID `10001:10001`;
- read-only container root filesystem;
- writable persistent `/data` bind mount only for application state;
- restricted `/tmp` tmpfs with `noexec` and `nosuid`;
- `no-new-privileges:true`;
- all Linux capabilities dropped;
- PID limit of 256;
- no privileged mode;
- no host networking;
- no Docker socket;
- no direct host-port publication;
- application attached only to the approved Caddy proxy network.

I will not weaken host filesystem permissions merely to make the container start. Before target deployment I will create or approve the persistent data directory, assign the ownership required by UID/GID 10001, apply restrictive permissions, and record the exact target path and resulting database-file permissions as target-environment evidence.

## Immutable build identity

The production image identity is tied to an exact Git commit SHA.

`docker-compose.production.yml` requires `GOREECLOUD_NOTIFY_BUILD_REVISION` and passes it directly to the `Dockerfile.production` build argument. Compose therefore fails before rendering the production contract if the revision is omitted. This prevents an operator from assigning an approved-looking image tag while accidentally building an image whose embedded `BUILD_REVISION` and OCI revision label still contain the `development` fallback.

For an approved build I set both `GOREECLOUD_NOTIFY_IMAGE_TAG` and `GOREECLOUD_NOTIFY_BUILD_REVISION` to the exact accepted 40-character Git SHA. The application independently rejects `development` as a build revision when `GOREECLOUD_NOTIFY_ENVIRONMENT=production`.

## Production configuration boundary

Production runtime configuration is separate from development defaults.

`GOREECLOUD_NOTIFY_ENVIRONMENT=production` activates fail-closed validation. Production startup requires:

- `GOREECLOUD_NOTIFY_SESSION_COOKIE_SECURE=true`;
- one or more approved absolute HTTPS CORS origins;
- no localhost development CORS origins;
- an explicit narrow `GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS` value for the approved Caddy-side Docker network;
- no whole-address-family proxy trust such as `0.0.0.0/0`;
- an immutable build revision rather than the `development` fallback.

The source-controlled template is `deploy/production/runtime.env.example`. It deliberately omits the final proxy CIDR so a copied template cannot silently become a valid production configuration before the target network is inspected and approved.

## Proxy and client-address trust

The production Uvicorn command disables Uvicorn proxy-header rewriting. I preserve the direct Docker peer address for the application so GoreeCloud Notify can enforce its own proxy trust boundary.

Login-abuse logic uses the immediate peer address first. It considers `X-Forwarded-For` only when that immediate peer belongs to `GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS`. This prevents an arbitrary caller from becoming a trusted source merely by supplying forwarding headers.

The final target proxy CIDR must therefore identify the actual narrow network from which approved Caddy traffic reaches GoreeCloud Notify. It must not be guessed from this repository.

## Secret handling

I do not store active production secrets in this repository, Compose files, examples, documentation, image layers, or Caddy fragments.

The production Compose contract requires `GOREECLOUD_NOTIFY_ENV_FILE` to point to a separately protected host-side runtime environment file. Before deployment I will validate its owner, group, mode, scope, backup/recovery treatment, and rotation procedure under the applicable GoreeCloud sensitive-information requirements.

The static bootstrap administrative token is not a routine production administration mechanism. If initial administrator bootstrap is still required on a new database, I will add a temporary high-entropy `GOREECLOUD_NOTIFY_ADMIN_TOKEN` only to the protected target runtime configuration, provision the initial administrator, verify the resulting administrator session, remove the bootstrap token from runtime configuration, and recreate the container without it. Routine administration uses authenticated administrator sessions.

## SQLite state and migration control

The production database is stored at `/data/goreecloud_notify.db` inside the application runtime and mapped from an approved persistent host directory.

I do **not** run `alembic upgrade head` as an automatic side effect of ordinary application container startup in the production contract.

Before a production schema change I will:

1. verify the current backup/recovery point required by the GoreeCloud backup and recovery controls;
2. stop or otherwise place the application in the approved change state;
3. run the explicit maintenance migration service:

   ```bash
   docker compose -f docker-compose.production.yml --profile maintenance run --rm migrate
   ```

4. verify the schema and application health;
5. start or replace the normal application service;
6. retain the documented rollback/recovery path if validation fails.

The maintenance migration service has `network_mode: none` because Alembic requires only the local SQLite bind mount for this application architecture.

## Proposed Caddy publication contract

`deploy/caddy/notify.goreecloud.com.caddy` records the future GoreeCloud Notify Caddy site block without installing it.

The fragment:

- uses `notify.goreecloud.com`;
- retains Porkbun DNS-01 credential placeholders rather than literal values;
- restricts the application route to the NetBird address space `100.64.0.0/10`;
- proxies to `goreecloud-notify:8000` over Docker networking;
- returns `403 Forbidden` to sources outside the approved address range;
- adds `Strict-Transport-Security: max-age=31536000` to HTTPS responses.

I intentionally do not add HSTS `includeSubDomains` or `preload` directives in this service fragment. Either directive expands policy beyond the single service boundary and requires a separate domain-level decision and validation.

I will **not** install this fragment while `notify.goreecloud.com` still serves ntfy. The actual production Caddyfile must be backed up and validated as a complete configuration before any controlled cutover.

## Disposable readiness gate

`.github/workflows/production-readiness.yml` validates the source-controlled production pattern without modifying GoreeCloud production.

The workflow uses only synthetic credentials and disposable Docker state. It verifies:

- production image build from the committed npm lock;
- final image UID/GID;
- immutable build revision in the image label and `/app/BUILD_REVISION`;
- production Compose refusal when the required build revision is absent;
- rendered production Compose propagation of the exact revision to both app and migration builds;
- production Compose structure and explicit maintenance migration separation;
- application read-only filesystem, capabilities, `no-new-privileges`, PID limit, writable paths, networks, and host-port absence;
- production configuration fail-closed behavior through the normal backend tests;
- private HTTPS through a pinned disposable Caddy image;
- HSTS on the approved HTTPS path;
- same-origin CORS behavior;
- `Secure`, `HttpOnly`, and `SameSite=strict` session cookies;
- application authentication after network authorization;
- authorized NetBird-range source access;
- `403` denial from a non-NetBird-range source;
- database-aware health checks;
- frontend index and immutable asset cache boundaries;
- SQLite persistence after removal and replacement of the application container;
- synthetic secret absence from runtime logs and image history;
- teardown of the disposable runtime and generated credentials.

The readiness Caddy topology uses an internal test certificate authority only. It does not request a Porkbun/ACME production certificate and does not alter DNS.

## Target-environment gate

Source-controlled readiness is necessary but not sufficient for deployment. Before I approve GoreeCloud Notify production use I still must record target-host evidence for:

- exact release/image identity;
- final persistent-data path and owner/group/mode;
- final protected environment-file owner/group/mode;
- final Docker network membership and absence of unnecessary host ports;
- final Caddy configuration validation, HSTS response, and trusted certificate for `notify.goreecloud.com`;
- private AdGuard Home resolution;
- approved and denied NetBird access tests;
- application authentication and session behavior through final HTTPS;
- backup and alternate-location restore evidence under issue #23;
- independent monitoring and Notify-down alert delivery under issue #24;
- producer migration and least-privilege credential evidence;
- application/runtime log review;
- upgrade and recovery behavior;
- tested rollback to the retained ntfy route/runtime during migration.

Until those checks are complete, ntfy remains production and the GoreeCloud Notify production Compose/Caddy files remain proposed configuration only.
