# Native notification idempotency

GoreeCloud Notify's native `POST /api/v1/notifications` ingestion path supports optional producer-supplied idempotency through the `Idempotency-Key` request header.

## Purpose

The contract prevents an at-least-once producer retry from creating a second `Notification` and a second subscription fanout after a transient timeout or uncertain response. It is intended for stable producer event identities such as a GoreeCloud Monitor state-transition record.

## Contract

- The key is optional for legacy producers. A request without the header preserves the existing non-idempotent write behavior.
- The header is limited to 512 characters and is scoped to the authenticated Notify `Source`.
- Notify never stores the producer-supplied key. It stores only a SHA-256 digest used for replay lookup.
- `(source_id, idempotency_digest)` is unique in the database. Different producer sources may independently use the same external key.
- The first successful write returns `201 Created`.
- An exact replay returns the original notification as `200 OK` with `Idempotency-Replayed: true` and does not fan out a second Delivery.
- Reusing a key for different channel, title, body, severity, or expiry data returns `409 Conflict` rather than silently accepting ambiguous content.
- Concurrent duplicate writes converge through the database uniqueness boundary. Only the winning transaction performs fanout; the losing transaction resolves to the committed original notification.

## Privacy boundary

Idempotency is a delivery-integrity mechanism, not notification content. Raw idempotency keys are excluded from persisted notification history, inbox Delivery objects, API read models, exports, and user-visible presentation. Producers should still avoid putting credentials, secrets, target URLs, IP addresses, or private diagnostics in their event identity.

This behavior strengthens the existing Privacy Shield data-minimization boundary; it does not broaden Privacy Shield's runtime authority or production-acceptance status.

## GoreeCloud Monitor producer

The bounded Monitor producer adapter derives an opaque versioned replay key from the monitoring event type plus a stable transition identifier. Presentation fields such as the monitor display label are deliberately excluded from replay identity so a rename cannot cause a duplicate notification. The internal transition identifier is not copied into Notify notification content.

Monitor remains authoritative for monitoring state. Notify remains authoritative for notification persistence and delivery. Successful publication is not health evidence, and Notify must not become the sole alert path for an outage of Notify itself.

## Acceptance boundary

Source implementation and automated tests do not constitute production acceptance. Before the Monitor producer path replaces an existing production notification route, representative transition retries, conflict behavior, authentication, failure handling, rollback, and live target delivery must be exercised with retained evidence.
