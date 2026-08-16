# User Subscription Administration — Milestone 2

PR #10 adds the first end-user subscription-management API for GoreeCloud Notify. It remains pre-production and does not change ntfy, producer configuration, DNS, Caddy, AdGuard Home, NetBird, firewall policy, or any production runtime.

## Ownership model

Subscription ownership is derived exclusively from the validated human `UserPrincipal`. The public user API does not accept a `user_id`, username, or other target-user field. Producer bearer tokens cannot authenticate to these endpoints.

`GET /api/v1/subscriptions` lists every approved Channel together with the authenticated user's current subscription state. A missing Subscription row and a disabled Subscription row both appear as `subscribed: false`.

## Mutations

`PUT /api/v1/subscriptions/{channel_slug}` enables the authenticated user's subscription. If no row exists, one is created. Repeating the operation is idempotent.

`DELETE /api/v1/subscriptions/{channel_slug}` disables the authenticated user's subscription when one exists. If no row exists, the endpoint still returns the channel as unsubscribed. Repeating the operation is idempotent.

Both mutation endpoints require the session-bound `X-CSRF-Token` introduced in PR #9. Unknown channel slugs return `404`.

## Delivery-history boundary

Subscription state controls future fanout only. Disabling a subscription must never delete or rewrite existing `Delivery` rows. A user who unsubscribes retains prior inbox history, receives no new Delivery for that Channel while disabled, and resumes future Delivery fanout after re-subscribing.

This distinction keeps routing preference separate from historical inbox state and prevents a preference change from becoming an implicit destructive-data operation.

## Data model and migration boundary

PR #10 reuses the existing `Subscription` table and unique `(user_id, channel_id)` constraint. No schema migration is required.

Disabled rows are retained rather than deleted so subscribe/unsubscribe remains an explicit state transition and can be re-enabled without creating duplicate ownership rows.

## Validation expectations

The PR #10 regression suite covers:

- listing approved channels with only the authenticated user's state
- CSRF enforcement for subscribe/unsubscribe
- idempotent enable/disable behavior
- cross-user isolation
- unknown-channel rejection
- producer-token rejection
- preservation of existing Delivery history after unsubscribe
- suppression of future fanout while disabled
- resumption of future fanout after re-subscribe

## Current boundary

PR #10 does not approve notification-retention duration, automatic purge behavior, destructive inbox deletion, public account recovery, production login rate controls, WebSocket/SSE delivery, mobile push, or ntfy production migration. Those require separate review and validation.