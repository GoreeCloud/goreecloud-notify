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

This slice reuses the Milestone 1 database schema and therefore does not require a schema migration.

## Current boundary

Native writes are enabled only in the pre-production PR #3 development API. There is no ntfy-compatible topic endpoint yet. There is also no authenticated end-user delivery/read/acknowledgement API, subscription fanout, WebSocket/SSE delivery, mobile push, attachment support, or production producer migration.

The next notification-engine slice is administrative notification history/read access followed by a separately reviewed ntfy-compatible ingestion adapter.

## Production boundary

`notify.goreecloud.com` continues to belong to ntfy. No Caddy, DNS, AdGuard Home, NetBird, producer configuration, firewall, mobile-client, or production-container change is made by these Milestone 2 slices.
