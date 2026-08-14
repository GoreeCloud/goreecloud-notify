# GoreeCloud Notify

GoreeCloud Notify is the original GoreeCloud-owned centralized notification-delivery application being developed as the long-term successor to ntfy.

> **Development status:** Milestone 4 real-time delivery development is stacked on the unmerged Milestone 2, Milestone 3, and production-readiness work. GoreeCloud Notify is not deployed and does not replace the current ntfy service at `https://notify.goreecloud.com`.

## Current development scope

The repository now contains four major development layers:

1. **Milestone 1 foundation** — FastAPI, React/TypeScript/Vite, SQLite/SQLAlchemy, Docker development topology, documentation, tests, and GitHub Actions.
2. **Milestone 2 notification engine** — producer identities and scoped tokens, sources/channels, native and initial ntfy-compatible ingestion, persistence, producer history, administrator-provisioned human users, opaque web sessions, subscription fanout, user-owned inbox state, CSRF protection, subscription administration, and non-destructive retention analysis.
3. **Milestone 3 Glaze UI Inbox** — authenticated web sign-in, session restoration, notification-center layout, server-backed search/filters, cursor pagination, user-owned channel subscription management, source/severity presentation, notification detail, read/unread and acknowledgement actions, fail-visible logout behavior, responsive accessibility controls, system/light/dark appearance selection, Chromium interaction validation, and automated WCAG A/AA checks.
4. **Milestone 4 real-time delivery** — an authenticated Server-Sent Events inbox stream, persisted Delivery cursors, replay semantics, long-lived session revalidation, native browser EventSource integration, live/reconnecting connection state, and stream-handshake inbox reconciliation.

The stacked hardening/readiness line also includes fail-closed session configuration, SQLite foreign-key enforcement, UTC datetime canonicalization, production administrator authorization, login abuse controls, administrator password reset, required-text normalization, backup/restore tooling and recovery validation, production runtime/private-publication readiness, and monitoring/outage-alert readiness.

All of those changes remain draft and pre-production until intentionally integrated.

## Milestone 3 web experience

The Glaze inbox uses the existing security contracts rather than creating separate frontend authentication, subscription, or preference models.

- `POST /api/v1/session` creates the HttpOnly human session and returns the session-bound CSRF token header.
- `GET /api/v1/me` restores an existing authenticated browser session.
- `GET /api/v1/csrf` restores the current CSRF token when a browser session already exists.
- `GET /api/v1/inbox` provides a bounded page of user-owned deliveries and accepts read/source/channel/severity/search/cursor filters.
- `q` performs case-insensitive user-scoped search across notification title/body plus source and channel names/slugs; SQL LIKE wildcard characters supplied by the user are escaped and treated literally.
- The web client debounces search, composes server-backed read/severity/source filters, cancels stale filter requests, and loads older results with the existing `before_id` cursor.
- `GET /api/v1/subscriptions` supplies the authenticated user's state for all available notification channels.
- The Glaze channel-management disclosure uses the existing CSRF-protected `PUT` and `DELETE /api/v1/subscriptions/{channel_slug}` endpoints rather than storing subscription state only in the browser.
- Unsubscribing affects future Delivery fanout for that account; it does not delete existing notification history. Resubscribing resumes future fanout under the existing backend contract.
- Read, unread, acknowledgement, subscription, and logout mutations use the existing session-bound CSRF protection.
- Browser API requests use `credentials: include`, preserving the production same-origin model while allowing the separate local Vite origin to use the development CORS configuration.
- A logout request that cannot confirm server-side session revocation leaves the authenticated UI active and presents an error rather than falsely reporting a successful sign-out.
- Theme preference is presentation-only browser state stored in local storage; it is not an authentication or server preference record.

The UI does not display producer tokens, session-cookie values, CSRF values, database configuration, or other reusable credentials.

## Milestone 4 real-time delivery

The first Milestone 4 slice uses Server-Sent Events because the current web requirement is one-way server-to-browser notification delivery. It does not add a WebSocket dependency merely for transport symmetry.

### Server stream contract

`GET /api/v1/inbox/stream` provides the authenticated user's real-time Delivery stream.

- The endpoint authenticates with the existing HttpOnly human-session cookie. Producer bearer tokens are not accepted as a substitute for a human session.
- Authentication is completed with a short-lived SQLAlchemy session before the `StreamingResponse` starts; no request-scoped authentication database session is intentionally held for the lifetime of the connection.
- The stream is user-isolated by `Delivery.user_id`.
- Delivery state is read from persisted SQLite data instead of process-local pub/sub state, so correctness does not depend on one particular application worker retaining an in-memory event.
- If no replay cursor is supplied, the connection snapshots the current latest owned Delivery ID and emits a `ready` event for that cursor. Newer deliveries are then emitted in ascending Delivery-ID order.
- Each `inbox` event uses the Delivery ID as the SSE event ID and carries the existing `InboxDeliveryRead` representation.
- `after_id` can explicitly request replay after a non-negative Delivery ID.
- `Last-Event-ID`, when supplied by an SSE client, takes precedence over `after_id`; malformed or negative header values fail with HTTP 400.
- The server advertises a 3-second SSE retry interval and emits periodic keepalive comments during otherwise idle connections.
- The backing `WebSession` is revalidated while the stream is open. Session revocation, password-reset session invalidation, user deactivation, absolute expiry, or idle expiry terminates continued stream authorization.
- Streaming responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

Central Caddy remains the intended HTTPS gateway. Its normal reverse-proxy behavior supports `text/event-stream` streaming, so this slice does not add a separate public listener or a second application gateway.

### Browser integration

The Glaze inbox uses the browser's native `EventSource` implementation with credentials enabled.

- Authenticated users open the SSE stream automatically.
- The interface reports connecting, live, reconnecting, or idle state in an accessible status region.
- A `ready` event triggers a normal server-backed inbox refresh so initial REST state is reconciled with the stream handshake.
- New events are deduplicated by Delivery ID and prepended when they satisfy the current simple read/source/severity view.
- When server-backed text search is active, a real-time event triggers a server refresh rather than duplicating search semantics in browser code.
- The browser gate passes a real mocked `text/event-stream` response through native Chromium `EventSource` parsing and verifies that the live Delivery appears without a manual refresh.
- The browser gate also verifies the reconnecting UI state when its finite synthetic stream closes. The backend test suite separately owns the `Last-Event-ID` parsing/replay contract because Playwright's static intercepted stream is not treated as proof of a complete reconnect network exchange.

### First-slice boundary

This slice establishes authenticated real-time transport and replay primitives, but it intentionally does **not** claim a complete offline synchronization protocol.

The next Milestone 4 work remains:

- a race-resistant cursor synchronization/reconciliation contract across REST load, stream handshake, disconnect, reconnect, and process restart;
- authoritative user-level unread counts rather than counts limited to the currently loaded result page;
- explicit stale/offline state and recovery behavior;
- browser Notifications API support only after permission, privacy, foreground/background, and UX behavior are deliberately approved;
- additional transport only if a later requirement cannot be met cleanly with SSE.

## Browser and accessibility validation

The frontend has a separate read-only GitHub Actions browser gate using locked Playwright and Axe dependencies.

The gate builds the immutable Vite artifact, installs Chromium for the CI runner, and validates isolated browser scenarios against synthetic API/stream contracts, including:

- authenticated inbox rendering and semantic navigation;
- native EventSource parsing of a synthetic live Delivery;
- visible live/reconnecting transport state;
- keyboard discovery of the skip-to-notifications link;
- server-backed unread filtering and debounced search requests;
- cursor-based `Load more` behavior;
- notification-channel subscription interaction with CSRF header validation in the mock contract;
- dark-mode state;
- narrow mobile rendering without horizontal document overflow;
- sign-in form labels and controls;
- automated Axe analysis for selected WCAG A/AA rule tags on authenticated and unauthenticated surfaces.

Automated browser and Axe checks are evidence for detectable interaction/accessibility problems, not proof of complete accessibility conformance. Manual keyboard, screen-reader, zoom/reflow, visual contrast/usability, and inclusive-user acceptance remain separate acceptance work.

## Repository structure

```text
.
├── backend/                    FastAPI API, SQLite model, migrations, recovery tooling
├── frontend/                   React + TypeScript + Vite web client and browser tests
├── deploy/                     Proposed production/private-publication and monitoring contracts
├── docs/                       Architecture, security, recovery, monitoring, migration
├── docker-compose.yml          Isolated development topology
├── Dockerfile.production       Production multi-stage frontend/backend image
└── .github/workflows/          CI and source-controlled readiness/browser gates
```

## Local backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
alembic -c alembic.ini upgrade head
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Local frontend

```bash
cd frontend
npm ci --ignore-scripts
npm run lint
npm run check
npm run build
npm run dev -- --host 127.0.0.1
```

For browser validation after installing the Playwright Chromium runtime for the current environment:

```bash
cd frontend
npm run test:browser
```

`frontend/package-lock.json` is committed and release/CI installs use the reproducible lock with `npm ci`.

## Docker development

```bash
docker compose config
docker compose up --build
```

Development host publications remain loopback-only. The production-readiness design does not publish the application backend directly to the host; central Caddy is intended to reach the application over the approved Docker proxy network after a separately controlled target deployment.

## Important API routes

### System

- `GET /healthz` — database-aware application health
- `GET /api/v1/meta` — development milestone and capability metadata

### Human sessions and inbox

- `POST /api/v1/session` — human login
- `DELETE /api/v1/session` — CSRF-protected logout
- `GET /api/v1/me` — current authenticated human profile
- `GET /api/v1/csrf` — current session-bound CSRF token
- `GET /api/v1/inbox` — user-owned Delivery history with `read`, `acknowledged`, `source`, `channel`, `severity`, `q`, `before_id`, and bounded `limit` query controls
- `GET /api/v1/inbox/stream` — session-authenticated SSE stream with persisted Delivery cursor/replay semantics
- `GET /api/v1/inbox/{delivery_id}` — user-owned Delivery detail
- `POST /api/v1/inbox/{delivery_id}/read` — mark read
- `DELETE /api/v1/inbox/{delivery_id}/read` — mark unread
- `POST /api/v1/inbox/{delivery_id}/acknowledge` — acknowledge and mark read
- `GET /api/v1/subscriptions` — all available channels plus the current user's owned subscription state
- `PUT /api/v1/subscriptions/{channel_slug}` — CSRF-protected idempotent subscribe/resubscribe
- `DELETE /api/v1/subscriptions/{channel_slug}` — CSRF-protected idempotent unsubscribe without deleting historical deliveries

### Producers and compatibility

- `POST /api/v1/notifications` — native scoped producer ingestion
- `GET /api/v1/notifications` — producer-scoped history
- `GET /api/v1/notifications/{id}` — producer-scoped detail
- `POST|PUT /{topic}` — initial authenticated ntfy-compatible publishing

Advanced ntfy features such as attachments, delayed delivery, email/calls, actions, and broader formatting semantics remain outside the implemented compatibility boundary unless separately approved.

## Production and migration boundary

ntfy v2.26.3 remains the active production notification service. Draft source-level readiness work does **not** constitute a production deployment.

Before controlled cutover, GoreeCloud Notify still requires the applicable target-environment evidence for runtime/private publication, backup/restore, monitoring, independent Notify-down alert delivery, and producer/consumer migration. No draft PR by itself authorizes DNS, Caddy, AdGuard Home, NetBird, firewall, Uptime Kuma, producer, subscriber, database, or ntfy retirement changes.

## Next roadmap

- **Milestone 3 acceptance:** manual browser/visual and accessibility review remains an independent acceptance activity for the Glaze interface.
- **Milestone 4:** continue from the implemented authenticated SSE transport into cursor synchronization/reconnect/offline semantics and authoritative unread counts; evaluate browser notifications only after those state semantics are stable.
- **Milestone 5:** Android client evaluation/implementation after web/API stability.
- **Milestone 6:** controlled ntfy migration with producer-by-producer validation and rollback.
- **Milestone 7:** GoreeCloud platform integrations.
- **Milestone 8:** iOS client after platform/signing/transport requirements are verified.

## License

The application license remains an open project decision. The repository remains private while the approved open-source license is selected and recorded.
