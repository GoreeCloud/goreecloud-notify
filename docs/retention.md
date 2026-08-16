# Retention Preview and Destructive-Data Safety — Milestone 2

PR #11 adds an administrator-only retention preview for GoreeCloud Notify. It is intentionally non-destructive and does not approve a retention duration, purge schedule, deletion policy, or production cleanup process.

## Purpose

The preview provides evidence for future retention-policy decisions without turning an unapproved age threshold into a deletion rule. An operator must provide an explicit UTC cutoff for every request. The cutoff is analysis input only.

The current candidate definition is strict:

```text
notification.created_at < cutoff
```

A Notification created exactly at the cutoff is not a candidate.

## Endpoint

```text
GET /api/v1/admin/retention/preview?cutoff=<explicit UTC timestamp>
```

The endpoint uses the existing bootstrap administrative authorization boundary and therefore requires `X-GoreeCloud-Admin-Token`. Human web sessions and producer bearer tokens do not replace that administrative authorization.

The cutoff must include UTC explicitly as `Z` or `+00:00`. Naive timestamps and non-UTC offsets are rejected. The API does not infer a cutoff from the current time and does not supply a default retention age.

## Preview output

The response is explicitly labeled:

- `mode: preview_only`
- `cutoff_basis: notification_created_at_before_cutoff`
- `destructive_action_enabled: false`

It reports:

- candidate Notification count
- dependent Delivery count
- read Delivery count
- unread Delivery count
- acknowledged Delivery count
- unacknowledged Delivery count
- candidate Notifications whose explicit `expires_at` is at or before the supplied cutoff
- oldest candidate Notification `created_at`
- newest candidate Notification `created_at`

The explicit-expiry count is informational. PR #11 does not define `expires_at` as an automatic hard-delete instruction and does not reconcile retention policy with expiry semantics.

## Non-destructive guarantee

The preview service issues read-only aggregate/select queries. It does not call `commit()`, `delete()`, `update()`, or any cleanup worker. There is no DELETE/POST purge route in this slice.

Regression tests compare Notification, Delivery, and User row counts before and after preview and require them to remain unchanged. The tests also verify strict cutoff behavior, administrative authorization, and UTC-only cutoff validation.

## No schema migration

PR #11 reuses existing Notification and Delivery fields and requires no Alembic revision.

## Decisions still required before destructive retention

A later destructive retention design must be separately approved and validated. At minimum it must resolve:

- default retention duration, if any
- whether retention differs by source, channel, severity, or user preference
- authoritative meaning of `Notification.expires_at`
- handling of unread records
- handling of acknowledged records
- hard delete versus soft delete/tombstone behavior
- Notification-to-Delivery transaction/cascade behavior
- protection against orphaned Delivery records
- backup retention and restore implications
- post-restore reconciliation when deleted data can reappear from older backups
- audit/evidence requirements for cleanup runs
- dry-run/preview comparison before execution
- operational scheduling and failure recovery
- production authorization and rate controls

Until those decisions are explicit, GoreeCloud Notify must not run automatic notification purging and must not expose a destructive retention endpoint.

## Production boundary

PR #11 is pre-production development only. It does not change ntfy, producer or subscriber configuration, DNS, Caddy, AdGuard Home, NetBird, firewall rules, mobile clients, backups, or the production GoreeCloud Notify runtime. ntfy remains the active production notification service until the separately controlled migration milestone is approved.