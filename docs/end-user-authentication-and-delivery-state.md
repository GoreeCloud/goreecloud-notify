# End-User Authentication and Delivery-State Design

This document began as the PR #6 design boundary for the first authenticated GoreeCloud Notify inbox. PR #7 implements the human login/session portion of this design in pre-production development. PR #8 implements subscription-based Delivery fanout plus authenticated read-only inbox list/detail access; Delivery read/unread and acknowledgement mutations remain unimplemented pending explicit CSRF protection.

## Goals

The authenticated inbox should:

- keep human user authentication separate from producer/service bearer tokens
- preserve the existing `User` entity as the human application identity
- allow each active user to see only their own notification deliveries by default
- provide explicit read/unread and acknowledgement semantics
- support later web, Android, and iOS clients without making the first web implementation depend on mobile push
- keep session revocation possible from the server side
- avoid storing reusable secrets in browser-accessible JavaScript storage
- preserve GoreeCloud privacy-by-default and least-privilege requirements

## Existing model constraints

Milestone 1 already defines:

- `User` for a human identity
- `Device` for a user-associated client device
- `Subscription` for a user's relationship to a `Channel`
- `Notification` for a producer-generated message
- `Delivery` for per-user state on a notification
- `Preference` for user-specific settings

`Delivery` is unique by `(notification_id, user_id)`. The design therefore treats `Delivery` as **user-level inbox state**, not as a per-device push-attempt record.

The current nullable `device_id` field on `Delivery` must not be interpreted as proof that a notification was delivered to exactly one device. If later mobile delivery requires per-device attempt, retry, provider, or receipt state, that should be modeled separately rather than overloading the user-level `Delivery` row. Any schema change for that purpose requires a separately reviewed migration.

## Human authentication boundary

Producer authentication and user authentication have different purposes and must remain separate.

Producer/service identities continue to use scoped bearer tokens such as `notifications:write` and `notifications:read`. Those tokens are not user login credentials and must not grant access to an end-user inbox.

For human users, PR #7 selects a native GoreeCloud account with a server-managed, opaque web session. Passwords use Argon2id through `argon2-cffi`; session tokens are cryptographically random and only SHA-256 digests are stored in the new `web_sessions` table. Initial accounts are administrator-provisioned. Self-registration and account recovery remain outside this slice.

The first web-session implementation should require:

- password verification through a mature password-hashing implementation
- no plaintext or reversibly encrypted password storage
- opaque session identifiers generated with a cryptographically secure source
- server-side session revocation
- session rotation after successful login and privilege-sensitive changes
- `Secure` and `HttpOnly` cookies in deployed HTTPS environments
- an appropriate `SameSite` policy
- CSRF protection for cookie-authenticated state-changing requests
- explicit logout that invalidates the server-side session
- configurable idle and absolute session expiration
- generic authentication-failure messages that do not expose whether an account exists
- rate controls for repeated authentication attempts before production approval
- no reusable user credentials in source control, ordinary documentation, logs, or notification bodies

Browser local storage or session storage should not contain long-lived reusable authentication tokens for the normal web login flow.

## User lifecycle

The first implementation should use the existing `User` identity fields rather than creating a second human-account model.

An inactive user must not be able to establish a new session. Disabling a user should invalidate or render unusable existing sessions through the chosen server-side session mechanism.

Self-service public signup is outside the initial GoreeCloud Notify scope. Account creation, password reset/recovery, administrator role assignment, and family-user onboarding require an explicit administrative workflow before production use.

The design does not assume that a producer `ServiceIdentity` can be converted into a human `User`, or vice versa.

## Inbox fanout model

When a `Notification` is accepted, a later fanout step may create a `Delivery` for each active user with an enabled `Subscription` to the notification's `Channel`.

The initial fanout rules should be deterministic:

1. resolve the notification channel
2. find enabled subscriptions for that channel
3. include only active users
4. create at most one `Delivery` for each `(notification_id, user_id)` pair
5. treat the unique constraint as an idempotency backstop rather than normal control flow
6. do not expose another user's delivery state to the authenticated user

No implicit global subscription or critical-alert bypass is approved by this design. If GoreeCloud later needs mandatory channels or administrator-enforced subscriptions, that behavior requires a separate authorization and policy decision.

## Read and unread semantics

`Delivery.read_at` is the authoritative per-user read-state field.

- unread: `read_at IS NULL`
- read: `read_at` contains the UTC timestamp when the user marked or caused the delivery to become read
- mark read: set `read_at` only for the authenticated user's delivery
- mark unread: clear `read_at` for the authenticated user's delivery

Reading one user's delivery must not change any other user's delivery state.

A producer's `notifications:read` history endpoint remains operational producer history and does not represent a human user's read/unread state.

## Acknowledgement semantics

`Delivery.acknowledged_at` represents an explicit user acknowledgement, not merely opening or reading the notification.

For the first implementation candidate:

- acknowledging a delivery sets `acknowledged_at` to the current UTC time
- acknowledgement also sets `read_at` if the delivery is still unread
- marking a delivery unread later does not automatically remove acknowledgement
- a general-purpose unacknowledge action is not included initially

This keeps acknowledgement as an intentional, higher-confidence state than read/unread. If later workflows require acknowledgement revocation, assignment, escalation, or multi-user quorum, they require separate product and audit semantics.

## Proposed web API shape

The following endpoint list records current implementation status and the remaining inbox design candidates:

- `POST /api/v1/session` — **implemented in PR #7**; authenticate a human user and establish a web session
- `DELETE /api/v1/session` — **implemented in PR #7**; invalidate the current session
- `GET /api/v1/me` — **implemented in PR #7**; return the authenticated human user's safe profile
- `GET /api/v1/inbox` — **implemented in PR #8**; list only that user's deliveries with bounded filters/pagination
- `GET /api/v1/inbox/{delivery_id}` — **implemented in PR #8**; return one owned delivery and hide non-owned IDs as not found
- `POST /api/v1/inbox/{delivery_id}/read` — mark owned delivery read
- `DELETE /api/v1/inbox/{delivery_id}/read` — mark owned delivery unread
- `POST /api/v1/inbox/{delivery_id}/acknowledge` — acknowledge owned delivery

The inbox should support bounded pagination and filters for unread/read, acknowledgement, source, channel, and severity. Search and broader Glaze UI inbox behavior belong to Milestone 3.

## Authorization rules

The authenticated human principal must be derived from the validated user session, not from request-supplied user identifiers.

For normal users:

- inbox queries must filter by the authenticated user's ID
- delivery mutations must verify ownership in the same database operation or equivalent authorization boundary
- changing a URL or numeric delivery ID must not expose another user's data
- producer tokens must not satisfy human-session dependencies

Administrator access to another user's inbox is not granted by default in this design. If administrative support access is later required, it needs an explicit role, audit trail, and privacy review.

## Device relationship

Devices are associated with users but do not determine inbox ownership. A user's web or mobile clients should observe the same user-level `Delivery` read and acknowledgement state after synchronization.

Per-device push registration, push-provider tokens, attempt history, retries, and delivery receipts remain later mobile/realtime work. Reusable mobile push credentials must remain protected and must not be copied into notification history or ordinary logs.

## Retention and deletion

Notification retention and Delivery cleanup must be implemented together so expired or deleted notification records do not leave orphaned user-state records. The current foundation does not yet document database-level cascade behavior as a production guarantee.

Before production retention jobs are enabled, the implementation must define:

- deletion order or database cascade behavior
- treatment of acknowledged records
- retention overrides, if any
- backup and restore expectations
- audit/evidence boundaries

GoreeCloud Notify remains a notification-delivery system rather than the authoritative permanent record for the originating event.

## Implementation gates

Before enabling cookie-authenticated inbox mutations, the implementation must document and test the remaining mutation-specific controls; PR #7 already satisfied the login/session subset of these gates:

- the selected password-hashing implementation
- server-side session storage and revocation
- cookie and CSRF behavior
- login/logout and expiration tests
- inactive-user behavior
- user isolation tests for list/detail/mutation endpoints
- idempotent fanout behavior
- read/unread and acknowledgement state transitions
- database migration requirements, if any
- backup/recovery implications for authentication and session state
- production rate-limit and monitoring requirements

## Current decision state

The approved development direction is the **separation of human sessions, producer tokens, and user-level Delivery state**. PR #7 selects Argon2id password hashes, administrator-provisioned users, opaque server-side sessions, and Alembic-managed schema evolution for the first web-login implementation. Production rate controls, account recovery, explicit CSRF tokens for inbox mutations, and the read/unread/acknowledgement mutation implementation remain open gates. Subscription fanout and read-only inbox access are implemented in PR #8.

PR #6 itself was design-only. PR #7 adds pre-production human-session runtime and database migration files. PR #8 adds read-only inbox/fanout behavior without a new schema migration. None of these slices changes an ntfy producer, Caddy route, DNS record, AdGuard Home rewrite, NetBird policy, firewall rule, mobile client, or production container.
