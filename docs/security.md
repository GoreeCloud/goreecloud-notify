# Security Boundaries

GoreeCloud Notify remains pre-production. The current stacked Milestone 2 development branches implement producer authorization and the first human-session foundation without changing the active ntfy service.

## Producer identities

- producer/service identities use individually scoped bearer tokens
- raw producer tokens are returned only when created; only SHA-256 digests are stored
- revoked, expired, or disabled producer identities are rejected
- producer history is source-isolated
- the ntfy-compatible adapter still requires GoreeCloud Notify authentication

## Human identities

The PR #7 authentication implementation keeps human credentials separate from producer tokens. PR #9 adds server-side synchronizer CSRF protection for cookie-authenticated state changes.

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
- each web session owns a cryptographically random synchronizer CSRF token stored in server-side session state
- login exposes the CSRF token through the `X-CSRF-Token` response header and `GET /api/v1/csrf` can recover it for an authenticated SPA
- state-changing inbox routes and logout require the matching `X-CSRF-Token` request header
- CSRF comparisons use constant-time comparison
- `SameSite=Strict` remains defense in depth rather than the only CSRF control
- the CSRF token is not an authentication credential and is only useful alongside the HttpOnly authenticated session cookie

Production login rate controls remain mandatory before production approval. Password recovery/reset, administrator roles, support impersonation, and public signup remain unimplemented.

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

Alembic owns persistent schema evolution. PR #7 adds the pre-auth baseline and human-authentication revisions. PR #9 adds `0003_csrf_delivery_mutations`, which adds `web_sessions.csrf_token`. Existing pre-CSRF sessions are assigned CSRF state and revoked during upgrade so users must establish a new session under the new protection. Startup verifies the CSRF-era schema instead of silently altering an existing database.
