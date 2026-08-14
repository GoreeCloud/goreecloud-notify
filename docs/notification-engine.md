# Notification Engine — Milestone 2

Milestone 2 is being implemented as focused, stacked pre-production slices. Nothing in these branches changes the active ntfy production service.

## Slice 1 — Identity and routing control plane

Implemented in PR #2:

- bootstrap administrative authorization through `X-GoreeCloud-Admin-Token`
- service identities for notification producers
- individually issued producer bearer tokens
- SHA-256 token digests at rest; plaintext token returned only at creation
- explicit token scopes
- token revocation
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
- response mapping to the resolved source and channel
- automated tests for persistence, source impersonation rejection, and missing-channel rejection

## Slice 3 — Producer notification history and detail access

Implemented in PR #4:

- `GET /api/v1/notifications` with required `notifications:read` scope
- `GET /api/v1/notifications/{id}` with required `notifications:read` scope
- history restricted to sources owned by the authenticated service identity
- cross-identity detail access returns `404` instead of exposing another producer's records
- optional source, channel, and severity filters
- bounded page size from 1 to 100 records
- stable descending integer-ID pagination through `before_id`
- endpoint and service tests for scope enforcement, source isolation, filters, and cursor behavior

## Slice 4 — Initial ntfy-compatible publishing adapter

Implemented in PR #5:

- authenticated HTTP `POST` and `PUT` to `/{topic}`
- required GoreeCloud Notify bearer token with `notifications:write`
- ntfy-compatible simple message body publishing
- `X-Message`/`Message`/`m`, `X-Title`/`Title`/`t`, and `X-Priority`/`Priority`/`prio`/`p` header aliases
- equivalent `message`, `title`, and `priority` query-parameter aliases
- ntfy topic-name validation up to 64 characters
- topic-to-approved-channel resolution
- producer source resolution that prefers exact or `goreecloud-`-stripped matches and otherwise allows only an unambiguous single source
- current GoreeCloud ntfy 4 KiB message-size limit
- priority translation into GoreeCloud severity: low/min → info, default → normal, high → warning, urgent/max → critical
- response envelope with ntfy-style `id`, `time`, `event`, `topic`, `message`, `title`, and `priority` fields
- explicit `422` rejection for unsupported advanced options such as tags, actions, click URLs, attachments, Markdown, delay, email, calls, Firebase, UnifiedPush, and poll IDs
- correction of missing-Authorization behavior so scoped endpoints return `401` instead of framework-level `422`

The adapter intentionally implements only the compatibility needed for safe incremental migration. It does not claim complete ntfy protocol compatibility.

## Slice 5 — End-user authentication and Delivery-state design

Recorded in PR #6 as a design-only slice:

- separates human user sessions from producer/service bearer tokens
- treats the existing `User` model as the human application identity
- treats `Delivery` as per-user inbox state because it is unique by notification and user
- defines unread as `read_at IS NULL` and read as a UTC `read_at` timestamp
- defines acknowledgement as an explicit `acknowledged_at` state that also marks an unread delivery read
- keeps producer history separate from human inbox state
- proposes server-managed opaque web sessions as the preferred implementation candidate while leaving the exact authentication implementation unapproved until the implementation PR
- defines ownership, session, cookie/CSRF, fanout, retention, and test gates before login code may be enabled
- explicitly avoids treating the current `Delivery.device_id` field as a complete per-device push-attempt model

PR #6 does not enable login routes, mutate the database schema, or alter production infrastructure.

## Slice 6 — Human authentication implementation

Implemented in PR #7:

- administrator-provisioned human accounts using the existing `User` model
- Argon2id password hashes through `argon2-cffi`
- opaque `gcs_` session identifiers generated with a cryptographically secure source
- SHA-256 session digests at rest in the new `web_sessions` table
- `POST /api/v1/session`, `DELETE /api/v1/session`, and `GET /api/v1/me`
- generic login failures and inactive-user rejection
- configurable absolute and idle session expiration
- `HttpOnly`, `SameSite=Strict` session cookies with a production `Secure` switch
- credentialed CORS limited to configured origins
- Alembic baseline and human-authentication migrations
- startup schema verification instead of using SQLAlchemy `create_all()` as a migration mechanism
- migration, session-expiration, session-rotation, logout-revocation, and plaintext-secret tests

This slice still does not implement public registration, password recovery, production login rate limits, explicit CSRF tokens for inbox mutations, subscription fanout, or user inbox read/acknowledgement routes.

Slices through PR #5 reuse the Milestone 1 database schema. PR #7 introduces the first reviewed schema evolution: an Alembic baseline plus a human-authentication migration that adds `users.password_hash` and `web_sessions`.


## Slice 7 — Subscription fanout and read-only user inbox

Implemented in PR #8:

- notification persistence now creates missing `Delivery` rows for active users with enabled subscriptions to the notification Channel
- fanout occurs inside the same transaction as notification persistence so the initial Notification and Delivery set commit together
- fanout is idempotent for an existing notification and relies on the existing unique `(notification_id, user_id)` constraint as a database backstop
- inactive users and disabled subscriptions do not receive Delivery rows
- native and ntfy-compatible publishing share the same fanout path
- `GET /api/v1/inbox` requires a validated human web session and filters by the authenticated user's ID
- `GET /api/v1/inbox/{delivery_id}` requires ownership; another user's delivery ID returns `404`
- inbox list filters support read/unread, acknowledged/unacknowledged, source, channel, and severity
- descending Delivery-ID pagination uses bounded `before_id` and `limit` parameters
- producer bearer tokens cannot authenticate to the human inbox

This slice adds no schema migration. It deliberately does **not** add cookie-authenticated read/unread or acknowledgement mutations; those remain blocked until explicit CSRF protection is implemented and validated.


## Slice 8 — CSRF-protected Delivery state mutations

Implemented in PR #9:

- server-side synchronizer CSRF token bound to each human `WebSession`
- login exposes `X-CSRF-Token`; `GET /api/v1/csrf` recovers the current session token for the authenticated SPA
- `DELETE /api/v1/session` now requires the valid session-bound CSRF header
- `POST /api/v1/inbox/{delivery_id}/read` marks only an owned Delivery read and is idempotent
- `DELETE /api/v1/inbox/{delivery_id}/read` marks only an owned Delivery unread without clearing acknowledgement
- `POST /api/v1/inbox/{delivery_id}/acknowledge` sets the first acknowledgement timestamp and also marks an unread Delivery read
- repeat acknowledgement preserves the original acknowledgement timestamp; no general unacknowledge route is implemented
- cross-user mutation attempts remain hidden as `404`, and producer bearer tokens cannot satisfy human mutation authentication
- SQLite-reloaded timestamps are normalized to UTC at the inbox API boundary for stable response semantics
- CORS explicitly allows and exposes `X-CSRF-Token`; `SameSite=Strict` remains defense in depth rather than the sole CSRF protection
- Alembic revision `0003_csrf_delivery_mutations` adds `web_sessions.csrf_token` and revokes existing pre-CSRF sessions during upgrade, requiring fresh login

The synchronizer token is server-side session state rather than an authentication credential. It is intentionally returned to authenticated browser code so the SPA can place it in a custom header, while the reusable session identifier remains in an `HttpOnly` cookie.

## Current boundary

Native writes and producer history are enabled only in the pre-production development stack. Producer history is operational history for service identities; it is not the eventual end-user notification inbox and does not implement Delivery read/unread or acknowledgement state.

The initial ntfy-compatible topic endpoint now exists for simple authenticated publishing, but advanced ntfy features remain unsupported and no production producer has been migrated to it. Human login and session validation exist in the pre-production PR #7 stack. PR #8 adds subscription-based Delivery fanout and authenticated inbox list/detail access. PR #9 adds the synchronizer CSRF mechanism and owned Delivery read/unread/acknowledgement mutations. WebSocket/SSE delivery, mobile push, attachment support, production producer migration, public account recovery, and production login rate controls remain unimplemented.

The end-user authentication and Delivery-state design is recorded in PR #6, PR #7 implements the selected human-session model plus schema migration, PR #8 implements inbox/fanout, and PR #9 implements CSRF-protected owned Delivery state transitions. The next code slice is subscription administration and Milestone 2 hardening.

## Production boundary

`notify.goreecloud.com` continues to belong to ntfy. No Caddy, DNS, AdGuard Home, NetBird, producer configuration, firewall, mobile-client, or production-container change is made by these Milestone 2 slices.
