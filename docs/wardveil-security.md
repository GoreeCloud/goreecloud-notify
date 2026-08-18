# GoreeCloud Notify — Wardveil Security integration

## Role and authority

GoreeCloud Notify uses **Wardveil Security by GoreeCloud** as the platform-wide security and protection identity for security-facing application presentation.

The approved protection-status phrase is **Protected by Wardveil**.

Wardveil is an identity and presentation layer. It does not replace or weaken GoreeCloud Notify's application authentication, authorization, session, CSRF, producer-token, input-validation, database-integrity, backup, monitoring, network, or deployment controls. Those controls and their governing GoreeCloud records remain authoritative for their technical state.

No new Wardveil product or module name is created by this integration.

## Application presentation contract

GoreeCloud Notify exposes its Wardveil relationship through sanitized application metadata and response headers:

- `/api/v1/meta` identifies `Wardveil Security`, `Wardveil Security by GoreeCloud`, and `Protected by Wardveil` while explicitly preserving application-control authority.
- HTTP responses include `X-Wardveil-Security: Protected by Wardveil`.
- The Wardveil response header is presentation metadata only. Clients must not treat it as proof that authentication, authorization, TLS, backup, monitoring, or another individual control succeeded.

Wardveil-facing application experiences remain subject to the Glaze UI design language. This integration does not create a competing visual system.

## Request correlation

Every HTTP response receives an `X-Request-ID` correlation identifier.

- A caller-supplied identifier is preserved only when it matches the bounded safe character contract.
- Invalid, malformed, or oversized identifiers are replaced with a server-generated identifier.
- The identifier is stored in request state for application-side diagnostic use.
- The same identifier is included in the structured HTTP event for the request.
- Generic unexpected-error responses include the identifier so an administrator can correlate a user-visible failure with server-side evidence without exposing internal exception details.

The request identifier is diagnostic context, not an authentication or authorization credential.

## Structured HTTP events

The backend emits compact JSON events through the `goreecloud.notify` logger for relevant request outcomes.

A normal request event records only:

- event type;
- service name;
- request identifier;
- HTTP method;
- normalized FastAPI route template when available;
- response status;
- bounded request duration.

An unexpected-error event adds only the Python exception class name. The raw exception message is deliberately excluded from the structured event.

Successful `/healthz` polling and immutable static-asset requests are intentionally suppressed from routine success logging to avoid high-volume low-value log collection. Their failures remain loggable.

## Sensitive-information boundary

The HTTP observability layer deliberately does **not** collect or emit:

- query strings;
- request or response bodies;
- cookies or session values;
- `Authorization` headers;
- CSRF values;
- producer tokens;
- administrator tokens;
- client IP addresses;
- user-agent strings;
- database URLs or database contents;
- environment dumps;
- raw unexpected-exception messages.

Authentication, authorization, administrator-audit, and login-security records remain owned by their dedicated application paths rather than being duplicated into broad HTTP access logs.

## Browser and response hardening

GoreeCloud Notify preserves its existing privacy/security response controls and additionally declares:

- `Cross-Origin-Opener-Policy: same-origin`;
- `Cross-Origin-Resource-Policy: same-origin`;
- `Origin-Agent-Cluster: ?1`;
- `X-Permitted-Cross-Domain-Policies: none`.

These controls complement the existing content-security policy, frame denial, no-referrer policy, no-sniff behavior, permissions policy, no-store private-response behavior, secure-cookie production requirement, and proposed private Caddy HSTS contract.

## Failure handling

Unexpected server failures return a generic `500` JSON response with a request identifier. The response does not expose the exception message, stack trace, credentials, internal path, query data, or other diagnostic internals.

If a response has already started, such as during an established streaming response, the middleware records the sanitized error event and allows the exception to propagate rather than attempting to send an invalid second response.

## Production and acceptance boundary

This source integration does not claim production deployment or production acceptance. It does not modify the live ntfy service, `notify.goreecloud.com`, Caddy, DNS, AdGuard Home, NetBird, firewall rules, backup schedules, monitoring registration, producer/consumer migration, credentials, or runtime state.

Target backup/restore, independent monitoring/out-of-band outage alerting, target runtime/private-publication evidence, manual browser/operating-system acceptance, controlled migration, and tested ntfy rollback remain separate required production gates.
