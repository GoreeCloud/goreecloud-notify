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

These implemented engine slices reuse the Milestone 1 database schema. A later user-authentication implementation may require a separately reviewed migration depending on the selected server-side session model.

## Current boundary

Native writes and producer history are enabled only in the pre-production development stack. Producer history is operational history for service identities; it is not the eventual end-user notification inbox and does not implement Delivery read/unread or acknowledgement state.

The initial ntfy-compatible topic endpoint now exists for simple authenticated publishing, but advanced ntfy features remain unsupported and no production producer has been migrated to it. There is also no authenticated end-user delivery/read/acknowledgement API, subscription fanout, WebSocket/SSE delivery, mobile push, attachment support, or production producer migration.

The end-user authentication and Delivery-state design is now recorded in PR #6. The next code slice may implement the selected session model and authenticated inbox only after the remaining authentication details are explicitly approved and tested.

## Production boundary

`notify.goreecloud.com` continues to belong to ntfy. No Caddy, DNS, AdGuard Home, NetBird, producer configuration, firewall, mobile-client, or production-container change is made by these Milestone 2 slices.
