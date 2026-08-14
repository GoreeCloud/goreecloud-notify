# Notification Engine — Milestone 2

Milestone 2 is being implemented as focused, stacked pre-production slices. Nothing in these branches changes the active ntfy production service.

## Slice 1 — Identity and routing control plane

Implemented in PR #2:

- bootstrap administrative authorization through `X-GoreeCloud-Admin-Token`
- service identities for notification producers
- individually issued producer bearer tokens
- SHA-256 token digests at rest; plaintext token returned only at creation
- explicit token scopes and token revocation
- producer-owned source administration
- channel administration
- source and channel inventory endpoints

## Slice 2 — Native notification ingestion and persistence

Implemented in PR #3:

- native `POST /api/v1/notifications`
- required `notifications:write` producer scope
- source and channel resolution
- producer source-ownership enforcement
- persistence through the existing `Notification` SQLAlchemy model
- response mapping to resolved source and channel
- automated persistence, source-impersonation, and missing-route tests

## Slice 3 — Producer notification history and detail access

Implemented in PR #4:

- `GET /api/v1/notifications` and `GET /api/v1/notifications/{id}` with required `notifications:read`
- history restricted to Sources owned by the authenticated ServiceIdentity
- cross-identity detail access hidden as `404`
- optional source, channel, and severity filters
- bounded page size and stable descending `before_id` pagination

## Slice 4 — Initial ntfy-compatible publishing adapter

Implemented in PR #5:

- authenticated HTTP `POST` and `PUT` to `/{topic}`
- required GoreeCloud Notify bearer token with `notifications:write`
- ntfy-compatible simple body publishing
- message/title/priority header and query aliases
- topic validation and topic-to-approved-channel resolution
- producer-source resolution without weakening service-identity ownership
- current GoreeCloud ntfy 4 KiB message-size boundary
- priority-to-severity translation
- ntfy-style response envelope
- explicit `422` rejection for unsupported advanced features including tags, actions, click URLs, attachments, Markdown, delay, email, calls, Firebase, UnifiedPush, and poll IDs
- missing Authorization corrected to return `401` rather than framework-level `422`

The adapter intentionally implements only the compatibility needed for safe incremental migration. It does not claim complete ntfy protocol compatibility.

## Slice 5 — End-user authentication and Delivery-state design

Recorded in PR #6 as a design-only slice:

- separates human user sessions from producer/service bearer tokens
- treats `Delivery` as per-user inbox state rather than mutating shared Notification content
- defines unread/read and acknowledgement semantics
- keeps producer history separate from human inbox state
- selects opaque server-managed sessions as the implementation direction subject to runtime validation
- defines ownership, cookie/CSRF, fanout, retention, and test gates before human mutation APIs are enabled
- avoids temporary client-supplied user-ID identity headers

PR #6 does not enable login routes or change the schema.

## Slice 6 — Human authentication implementation

Implemented in PR #7:

- administrator-provisioned human users
- Argon2id password hashes
- opaque `gcs_` session identifiers
- SHA-256 session digests at rest in `web_sessions`
- `POST /api/v1/session`, `DELETE /api/v1/session`, and `GET /api/v1/me`
- generic login failures and inactive-user rejection
- configurable absolute and idle session expiration
- `HttpOnly`, `SameSite=Strict` cookies with a production `Secure` switch
- credentialed CORS restricted to configured origins
- Alembic baseline and human-authentication migration
- startup schema verification instead of `create_all()` as a migration mechanism

Production login rate controls and account recovery remain outside this slice.

## Slice 7 — Subscription fanout and read-only user inbox

Implemented in PR #8:

- notification persistence creates missing `Delivery` rows for active users with enabled subscriptions to the Channel
- fanout occurs in the notification transaction and is idempotent with the existing unique constraint as a backstop
- inactive users and disabled subscriptions do not receive new Deliveries
- native and ntfy-compatible publishing share the fanout path
- `GET /api/v1/inbox` requires a validated human session and is scoped to the current user
- `GET /api/v1/inbox/{delivery_id}` requires ownership; another user's ID is hidden as `404`
- read/acknowledgement/source/channel/severity filters and bounded pagination
- producer bearer tokens cannot authenticate to the human inbox

This slice deliberately keeps the inbox read-only until explicit CSRF protection is available.

## Slice 8 — CSRF-protected Delivery state mutations

Implemented in PR #9:

- server-side synchronizer CSRF token bound to each `WebSession`
- login exposes `X-CSRF-Token`; `GET /api/v1/csrf` recovers it for the authenticated SPA
- CSRF-protected logout
- owned Delivery mark-read, mark-unread, and acknowledge mutations
- acknowledgement marks an unread Delivery read and repeat acknowledgement preserves the original timestamp
- cross-user mutation attempts remain hidden as `404`
- producer bearer tokens cannot satisfy human mutation authentication
- SQLite-loaded timestamps are normalized to UTC at the API boundary
- CORS allows/exposes `X-CSRF-Token`; `SameSite=Strict` remains defense in depth
- Alembic revision `0003_csrf_delivery_mutations` adds `web_sessions.csrf_token` and revokes existing pre-CSRF sessions during upgrade

## Slice 9 — User-owned subscription administration

Implemented in PR #10:

- `GET /api/v1/subscriptions` shows the authenticated user's state across approved Channels
- `PUT /api/v1/subscriptions/{channel_slug}` idempotently creates or enables the current user's subscription
- `DELETE /api/v1/subscriptions/{channel_slug}` idempotently disables it
- identity is derived only from the validated human session; no target-user field is exposed
- mutations require the session-bound CSRF token
- disabling a subscription affects future fanout only
- existing Delivery history is preserved
- re-enabling a subscription resumes future fanout
- no schema migration is required

## Slice 10 — Non-destructive retention preview

Implemented in PR #11:

- `GET /api/v1/admin/retention/preview` behind the existing bootstrap administrative authorization boundary
- explicit UTC cutoff is mandatory; no default retention age is encoded
- candidate rule is strictly `notification.created_at < cutoff`
- reports candidate Notification and dependent Delivery counts
- reports read/unread and acknowledged/unacknowledged Delivery breakdowns
- reports how many candidate Notifications are explicitly expired by the supplied cutoff
- reports oldest/newest candidate timestamps
- response identifies `mode: preview_only` and `destructive_action_enabled: false`
- implementation performs read-only aggregate queries
- regression tests verify Notification, Delivery, and User row counts do not change
- no schema migration is required

The supplied cutoff is analysis input only. PR #11 does not approve a retention duration, `expires_at` deletion semantics, hard-delete/soft-delete policy, cleanup scheduler, purge worker, or destructive endpoint.

## Slice 11 — Inactive-user session revocation hardening

Implemented in PR #12:

- corrects the inactive-user branch of `require_user_session()` so `WebSession.revoked_at` is committed when an already-authenticated User becomes inactive
- adds regression coverage for login while active, later database deactivation, persistent revocation on the first rejected request, and rejection of the same cookie as an invalid session afterward
- changes no session API contract and requires no schema migration

PR #12 exact head `bfb099632258575d76d07a61ff062d1a2538c31f` passed GitHub Actions run `31770091699` with 56 backend tests and the frontend pipeline green.

## Slice 12 — Metadata-driven frontend development status

Implemented in draft PR #13, pending exact-head CI execution:

- removes stale hard-coded `Milestone 1 · Foundation` status from the Glaze UI landing page
- fetches `/healthz` and `/api/v1/meta` independently
- derives displayed development milestone, next milestone, next slice, and implemented-engine count from backend metadata
- exposes a distinct metadata-unavailable state instead of leaving the page indefinitely in a loading state
- keeps backend health separate from roadmap metadata availability
- updates README through PR #13 and documents the exact-head validation boundary

Current PR #13 head is `13691d0fef040550d7b4f4ef67b70f20dfd3a0d4`. GitHub Actions runs `31785515288` and `31786223824` were both prevented from starting runners because GitHub reported recent account payment failure or an insufficient Actions spending limit. Those workflow results are external CI-account blocks, not code/test failures. The `App.tsx` implementation produced zero provisional local TypeScript transpile syntax diagnostics, but full dependency install, lint, project type-check, Vite build, and backend CI remain unverified. PR #13 must remain draft and unmerged until exact-head CI can actually execute.

## Schema evolution summary

- PRs #2–#5 reuse the Milestone 1 schema.
- PR #7 introduces the Alembic baseline and human-authentication schema evolution, including `users.password_hash` and `web_sessions`.
- PR #9 adds `web_sessions.csrf_token` and revokes pre-CSRF sessions through migration `0003_csrf_delivery_mutations`.
- PRs #8, #10, #11, #12, and #13 require no additional schema migration.

## Current boundary

Native writes and producer history exist only in the pre-production development stack. Producer history is operational history for service identities; the human inbox uses per-user Delivery state.

The initial ntfy-compatible topic endpoint supports only the documented simple authenticated publishing subset. Advanced ntfy features remain unsupported and no production producer has been migrated.

Human login/session validation, subscription-based Delivery fanout, authenticated inbox access, CSRF-protected Delivery state, and user-owned subscription administration are implemented in the stacked development branches. Retention is analysis-only: no destructive retention path is approved or implemented.

Production login rate controls, account recovery, a final retention/deletion policy, backup/restore reconciliation for cleanup, full ntfy feature compatibility, WebSocket/SSE delivery, mobile push, attachment support, and production producer migration remain incomplete.

PR #13 is the current top draft but does not have executable exact-head CI evidence because GitHub Actions is account-blocked. No later code slice should be treated as validated by inheriting PR #12's green result.

## Production boundary

`notify.goreecloud.com` continues to belong to ntfy v2.26.3. No Caddy, DNS, AdGuard Home, NetBird, producer configuration, firewall, mobile-client, production-container, or destructive-retention change is made by these Milestone 2 slices.
