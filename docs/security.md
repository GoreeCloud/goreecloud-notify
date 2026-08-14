# Security Boundaries

GoreeCloud Notify remains pre-production. The current stacked Milestone 2 development branches implement producer authorization and the first human-session foundation without changing the active ntfy service.

## Producer identities

- producer/service identities use individually scoped bearer tokens
- raw producer tokens are returned only when created; only SHA-256 digests are stored
- revoked, expired, or disabled producer identities are rejected
- producer history is source-isolated
- the ntfy-compatible adapter still requires GoreeCloud Notify authentication

## Human identities

The PR #7 authentication implementation keeps human credentials separate from producer tokens.

- human accounts use the existing `User` model
- accounts are administrator-provisioned; public self-registration is not enabled
- passwords are stored as Argon2id hashes through `argon2-cffi`
- authentication failures are generic to reduce username-enumeration signals
- inactive users cannot establish sessions
- web session identifiers are cryptographically random and opaque
- only SHA-256 session digests are stored in the database
- sessions have configurable absolute and idle expiration
- successful logins create new session identifiers
- logout revokes the server-side session
- browser session cookies are `HttpOnly` and `SameSite=Strict`
- deployed HTTPS environments must enable the `Secure` cookie attribute
- reusable authentication tokens are not stored in browser local storage

Explicit CSRF-token handling and production login rate controls remain mandatory before cookie-authenticated inbox mutation endpoints are enabled. Password recovery/reset, administrator roles, support impersonation, and public signup remain unimplemented.

## Runtime and network controls

- development ports remain loopback-only
- backend container runs as a non-root user
- container filesystems are read-only except explicit data/tmp locations
- Linux capabilities are dropped and `no-new-privileges` is enabled
- SQLite persistent state is kept outside the writable container layer
- credentialed CORS is restricted to explicitly configured development origins
- no Docker socket is exposed
- no Caddy, DNS, NetBird, firewall, ntfy, or production credential changes are made by these branches

## Database migration boundary

Alembic now owns persistent schema evolution. The authentication slice adds a full pre-auth baseline revision and a second migration for `users.password_hash` plus `web_sessions`. Startup verifies the required schema instead of silently altering an existing database.
