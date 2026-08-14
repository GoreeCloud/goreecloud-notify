# Notification Engine — Milestone 2

The first Milestone 2 slice establishes the identity and routing control plane. It is pre-production and does not enable notification writes yet.

## Implemented in this slice

- bootstrap administrative authorization through `X-GoreeCloud-Admin-Token`
- service identities for notification producers
- individually issued producer bearer tokens
- SHA-256 token digests at rest; plaintext token returned only at creation
- explicit token scopes
- token revocation
- producer-owned source administration
- channel administration
- source and channel inventory endpoints

The implementation reuses the Milestone 1 database tables and therefore does not require a schema migration.

## Next slice

The next Milestone 2 slice will connect scoped producer identities to notification ingestion and persistence. Native publishing and ntfy-compatible ingestion remain disabled until that code is separately implemented and validated.

User authentication, delivery fanout, subscriptions, read state, acknowledgement APIs, WebSocket/SSE delivery, mobile push, and production migration remain later work.

## Production boundary

`notify.goreecloud.com` continues to belong to ntfy. No Caddy, DNS, AdGuard Home, NetBird, producer configuration, or production container is changed by this milestone.
