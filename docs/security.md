# Security Boundaries

GoreeCloud Notify remains pre-production. The current stacked development line implements the source-level security controls below without changing the active ntfy production service.

## Producer identities

- producer/service identities use individually scoped bearer tokens
- raw producer tokens are returned only when created; only SHA-256 digests are stored
- revoked, expired, or disabled producer identities are rejected
- producer history is source-isolated
- the ntfy-compatible adapter still requires GoreeCloud Notify authentication
- producer/service bearer tokens cannot satisfy human administrator authorization, including tokens with broad producer scope

## Human identities and sessions

- human accounts are administrator-provisioned; public self-registration is not enabled
- passwords are stored as Argon2id hashes through `argon2-cffi`
- authentication failures remain generic to reduce username-enumeration signals
- inactive users cannot establish or continue authenticated sessions
- web session identifiers are cryptographically random and opaque
- only SHA-256 session digests are stored in the database
- sessions have configurable absolute and idle expiration
- successful logins create new session identifiers
- logout revokes the server-side session
- browser session cookies are `HttpOnly` and `SameSite=Strict`
- production configuration requires the `Secure` cookie attribute
- reusable authentication tokens are not stored in browser local storage
- each web session owns a cryptographically random synchronizer CSRF token stored in server-side session state
- login exposes the CSRF token through the `X-CSRF-Token` response header and `GET /api/v1/csrf` can recover it for an authenticated SPA
- cookie-authenticated state changes require the matching `X-CSRF-Token` request header
- CSRF comparisons use constant-time comparison
- `SameSite=Strict` remains defense in depth rather than the only CSRF control

## Administrator authorization and recovery

- normal administrative APIs require an attributable human administrator session
- `User.is_admin` is checked from current database state for privileged requests
- administrative mutations require the session-bound CSRF control
- the bootstrap administrator token is limited to first-administrator initialization rather than routine administration
- bootstrap initialization is recorded without storing the raw bootstrap credential
- removing administrator privilege takes effect for an already-issued session on the next privileged request
- deactivating an administrator invalidates continued privileged use through the normal session path
- administrator-controlled password reset replaces the password through the approved Argon2id path
- password reset revokes all active web sessions for the affected user and requires a fresh login
- reset events are attributable in administrative audit history without storing plaintext password material
- self-service email recovery is not implemented or assumed

## Login abuse controls

- login failure state is persisted so the policy is not process-local
- controls apply to both source-plus-account and source-wide failure patterns
- repeated abuse produces HTTP 429 with `Retry-After`
- successful login does not erase unrelated source-wide abuse history
- stale rate state and security-event history are bounded by configured cleanup/retention periods
- account and client signals stored for abuse controls are digested rather than preserving plaintext usernames or IP addresses in the rate/audit state
- forwarded client addresses are ignored unless the direct peer belongs to an explicitly configured trusted proxy CIDR
- malformed forwarded chains fail back to the trusted direct peer rather than trusting attacker-supplied text

## Response privacy, browser isolation, and caching

GoreeCloud Notify treats application responses as private by default and constrains the production browser document to the resources the current same-origin application actually requires.

### Cache and metadata exposure controls

- every non-asset HTTP response is emitted with `Cache-Control: no-store`
- non-asset responses also emit `Pragma: no-cache` for legacy cache behavior
- responses emit `X-Content-Type-Options: nosniff`
- responses emit `Referrer-Policy: no-referrer`
- authenticated API responses therefore do not rely on browser, proxy, or intermediary defaults to avoid storage
- the SSE inbox stream retains the same no-store policy while continuing to stream normally
- the built HTML shell remains no-store
- fingerprinted frontend assets under `/assets/` retain `public, max-age=31536000, immutable` caching so the privacy rule does not destroy immutable-asset performance

### Content Security Policy

The current production application uses a same-origin CSP:

`default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; frame-src 'none'; form-action 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'none'; worker-src 'none'; manifest-src 'self'`

The policy intentionally:

- permits the built JavaScript, CSS, fonts, images, fetch requests, and EventSource connection only from the GoreeCloud Notify origin, except that image data URLs remain permitted
- prevents plugin/object content
- prevents the application from being embedded in another page
- prevents framed child content
- prevents document base-URL rewriting
- restricts form submission to the application origin
- disables workers/service workers in the current web-only source line; adding a service worker or Web Push architecture requires an explicit later policy change and validation
- blocks media loading because the current Notify interface has no media-delivery requirement

The current frontend has no inline-script requirement. Production frontend resources are emitted as built same-origin assets. Development through the separate Vite development server is not governed by the production document response header.

### Framing and browser capability restrictions

- `X-Frame-Options: DENY` is retained as legacy defense in depth alongside CSP `frame-ancestors 'none'`
- `Permissions-Policy` disables camera, microphone, geolocation, payment, and USB capabilities because GoreeCloud Notify does not require them
- browser notification permission remains governed separately by the explicit opt-in notification design; the capability policy does not grant or simulate notification permission

The cache and browser-security policies are application-layer controls. They do not authorize deployment behind a caching proxy, CDN, or reverse proxy that overrides or weakens application response headers.

## Browser system-notification privacy

- browser system notifications are disabled by default
- notification permission is requested only after explicit user action
- denial or later permission revocation fails closed and removes the browser-local enabled state
- OS-level notification content uses a fixed generic GoreeCloud Notify title/body rather than Delivery title, body, source, channel, account identifiers, or protected details
- system alerts are suppressed while the page is visible
- replay/backlog activity does not create notification storms
- browser notification enablement is local browser preference state and is not an authentication credential

## Runtime and network controls

- development ports remain loopback-only
- the production-pattern backend runs as a non-root user
- container filesystems are read-only except explicit data/tmp locations
- Linux capabilities are dropped and `no-new-privileges` is enabled
- SQLite persistent state is kept outside the writable container layer
- production readiness uses an explicit migration step rather than relying on silent schema mutation during ordinary application startup
- credentialed CORS is restricted to configured origins
- no Docker socket is exposed to the application
- source-controlled production readiness proves a private HTTPS/Caddy path, authorized/unauthorized source behavior, Secure-cookie behavior, response cache/browser-security headers, persistence across application replacement, and secret-minimization checks in disposable infrastructure
- source-controlled monitoring readiness proves database-aware health monitoring, least-privilege alert identities, and controlled DOWN/RECOVERED transitions in disposable infrastructure

These source-level controls do not replace target-environment validation. Final Caddy, private DNS, NetBird authorization, filesystem permissions, backup/restore, monitoring, out-of-band outage alerting, and rollback evidence remain separate release gates.

## Database and recovery boundary

- Alembic owns persistent schema evolution
- SQLite foreign-key enforcement is enabled for normal application and migration connections
- client-supplied expiration timestamps require explicit timezone information and are canonicalized to UTC before SQLite persistence
- the repository provides an SQLite Online Backup API recovery tool and alternate-location synthetic restore regression
- restored human sessions are explicitly invalidated before normal use of a historical restore
- producer-token, user-active-state, administrator-authority, and other security-state reconciliation after a materially stale restore remain deliberate recovery decisions rather than silently trusted historical state

## Production boundary

The security controls in this document describe the current source-controlled stable-candidate line. They do not authorize a production deployment or ntfy retirement.

Before stable production classification, GoreeCloud Notify still requires the separately tracked manual browser/accessibility acceptance, target backup/restore evidence, target monitoring and independent outage-alert evidence, target private-publication/runtime evidence, approved open-source license integration, and controlled migration/rollback validation.
