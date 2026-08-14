# GoreeCloud Notify

GoreeCloud Notify is the original GoreeCloud-owned centralized notification-delivery application being developed as the long-term successor to ntfy.

> **Development status:** Milestone 4 real-time delivery development is stacked on the unmerged Milestone 2, Milestone 3, and production-readiness work. GoreeCloud Notify is not deployed and does not replace the current ntfy service at `https://notify.goreecloud.com`.

## Current development scope

The repository now contains four major development layers:

1. **Milestone 1 foundation** — FastAPI, React/TypeScript/Vite, SQLite/SQLAlchemy, Docker development topology, documentation, tests, and GitHub Actions.
2. **Milestone 2 notification engine** — producer identities and scoped tokens, sources/channels, native and initial ntfy-compatible ingestion, persistence, producer history, administrator-provisioned human users, opaque web sessions, subscription fanout, user-owned inbox state, CSRF protection, subscription administration, and non-destructive retention analysis.
3. **Milestone 3 Glaze UI Inbox** — authenticated web sign-in, session restoration, notification-center layout, server-backed search/filters, cursor pagination, user-owned channel subscription management, source/severity presentation, notification detail, read/unread and acknowledgement actions, fail-visible logout behavior, responsive accessibility controls, system/light/dark appearance selection, Chromium interaction validation, and automated WCAG A/AA checks.
4. **Milestone 4 real-time delivery** — an authenticated Server-Sent Events inbox stream, persisted Delivery cursors, replay semantics, long-lived session revalidation, authoritative inbox aggregate state, cursor-bootstrap synchronization, native browser EventSource integration, live/reconnecting/offline state, stream-handshake reconciliation, and explicit online recovery from the last Delivery actually processed by the browser.

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

Milestone 4 currently uses Server-Sent Events because the web requirement is one-way server-to-browser notification delivery. It does not add a WebSocket dependency merely for transport symmetry.

### Server stream contract

`GET /api/v1/inbox/stream` provides the authenticated user's real-time Delivery stream.

- The endpoint authenticates with the existing HttpOnly human-session cookie. Producer bearer tokens are not accepted as a substitute for a human session.
- Authentication is completed with a short-lived SQLAlchemy session before the `StreamingResponse` starts; no request-scoped authentication database session is intentionally held for the lifetime of the connection.
- The stream is user-isolated by `Delivery.user_id`.
- Delivery state is read from persisted SQLite data instead of process-local pub/sub state, so correctness does not depend on one particular application worker retaining an in-memory event.
- Each `inbox` event uses the Delivery ID as the SSE event ID and carries the existing `InboxDeliveryRead` representation.
- `after_id` can explicitly request replay after a non-negative Delivery ID.
- `Last-Event-ID`, when supplied by an SSE client, takes precedence over `after_id`; malformed or negative header values fail with HTTP 400.
- The server advertises a 3-second SSE retry interval and emits periodic keepalive comments during otherwise idle connections.
- The backing `WebSession` is revalidated while the stream is open. Session revocation, password-reset session invalidation, user deactivation, absolute expiry, or idle expiry terminates continued stream authorization.
- Streaming responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

Central Caddy remains the intended HTTPS gateway. The source-level design does not add a separate public listener or second application gateway for SSE.

### Authoritative inbox state

`GET /api/v1/inbox/state` provides one user-scoped synchronization snapshot containing:

- `latest_delivery_id` — the newest persisted Delivery ID owned by the authenticated user, or `0` for an empty inbox;
- `total_count` — the authenticated user's total Delivery count;
- `unread_count` — the total number of owned Deliveries where `read_at` is unset;
- `acknowledged_count` — the total number of owned Deliveries where `acknowledged_at` is set.

Those aggregate values are calculated server-side in one user-scoped database query. The Glaze UI no longer presents a loaded 50-item page count as though it were the user's total unread state.

The SSE `ready` event carries the same authoritative state together with the active replay cursor. The stream also emits `state` events when aggregate state changes, including read or acknowledgement activity from another browser tab or client that does not create a new Delivery.

### Cursor-bootstrap synchronization

The browser establishes the real-time connection with an explicit synchronization sequence:

1. restore the authenticated human session;
2. load `GET /api/v1/inbox/state` and retain its `latest_delivery_id` as the initial stream cursor;
3. load/render the normal server-backed inbox page independently;
4. open `EventSource` with `after_id=<snapshot latest_delivery_id>`;
5. accept realtime Delivery/state events only after a valid `ready` synchronization snapshot is received;
6. refresh the normal REST inbox on every valid `ready` event.

This sequence closes the ordinary race where a Delivery can be created between the browser's initial REST inbox load and the real-time connection: anything newer than the retained state cursor is replayable through the stream, while the post-handshake REST refresh reconciles the displayed page and deduplicates by Delivery ID.

The initial bootstrap cursor is deliberately not rewritten from aggregate state. Browser reconnect/recovery correctness is based on Delivery IDs the client has actually processed, not merely IDs the server reports as existing.

### Browser integration, stale state, and explicit offline recovery

The Glaze inbox uses the browser's native `EventSource` implementation with credentials enabled.

- The interface reports connecting, live, reconnecting, offline, or idle state in an accessible status region.
- `offline` is used only when the browser reports `navigator.onLine === false`. This is a browser connectivity signal, not an end-to-end assertion that the GoreeCloud network or Notify backend is healthy.
- If the browser reports online but Notify cannot be reached, EventSource failure remains `reconnecting` rather than being mislabeled offline.
- When the browser is explicitly offline, the hook does not hold or create an EventSource and the interface states that loaded results are stale until network recovery.
- While reconnecting with browser connectivity available, the client periodically revalidates `GET /api/v1/me`. An HTTP 401 clears the authenticated UI instead of leaving a revoked or expired session looking active indefinitely.
- After any transport error or explicit stream restart, Delivery and aggregate-state events are ignored until a fresh valid `ready` snapshot re-establishes synchronization.
- Malformed synchronization snapshots do not become authoritative UI state.
- A valid `ready` event updates authoritative counts and triggers a normal server-backed inbox reconciliation.
- New Delivery events are deduplicated by Delivery ID and prepended when they satisfy the current simple read/source/severity view.
- When server-backed text search is active, a real-time event triggers a server refresh rather than duplicating search semantics in browser code.
- Read, unread, or acknowledgement mutations refresh authoritative aggregate state and immediately reconcile the current filtered inbox rather than waiting for the periodic SSE state poll.

The explicit offline-recovery cursor advances **only after a valid Delivery event has actually been processed by the browser**. It is not advanced from `latest_delivery_id` in an aggregate `ready` or `state` snapshot, because doing that could move the recovery boundary past a Delivery that exists on the server but has not yet been consumed by the client.

When the browser transitions back online, the hook creates a fresh EventSource using `after_id=<last processed Delivery ID>`. The server can replay any later Deliveries, a new valid `ready` snapshot must restore synchronization before replayed events are trusted, and the normal post-ready REST refresh reconciles the visible inbox page.

### Current Milestone 4 boundary

The implemented synchronization model now covers authoritative counts, cursor bootstrap, persisted replay primitives, post-handshake reconciliation, cross-client aggregate-state events, fail-closed resynchronization, reconnecting/stale state, explicit browser offline state, and deterministic online recovery from the last processed Delivery cursor.

Remaining Milestone 4 work includes:

- deliberate browser Notifications API permission/privacy/foreground/background behavior before enabling system notifications;
- manual multi-tab, extended network-interruption, and recovery acceptance beyond automated synthetic browser coverage;
- target-environment validation of the real-time path before any production migration;
- additional transport only if a later requirement cannot be met cleanly with SSE.

## Browser and accessibility validation

The frontend has a separate read-only GitHub Actions browser gate using locked Playwright and Axe dependencies.

The gate builds the immutable Vite artifact, installs Chromium for the CI runner, and validates isolated browser scenarios against synthetic API/stream contracts, including:

- authenticated inbox rendering and semantic navigation;
- native EventSource parsing of a synthetic live Delivery;
- `after_id` bootstrap from the authoritative server cursor;
- authoritative total/unread/read navigation counts that exceed the loaded page size;
- live/reconnecting transport state;
- forced Chromium offline state with explicit stale-data presentation;
- forced online recovery that opens a fresh stream from the last processed Delivery cursor (`after_id=501` after Delivery 501 was consumed);
- immediate server-backed reconciliation after a read mutation in a filtered unread view;
- keyboard discovery of the skip-to-notifications link;
- server-backed unread filtering and debounced search requests;
- cursor-based `Load more` behavior;
- notification-channel subscription interaction with CSRF header validation in the mock contract;
- dark-mode state;
- narrow mobile rendering without horizontal document overflow;
- sign-in form labels and controls;
- automated Axe analysis for selected WCAG A/AA rule tags on authenticated and unauthenticated surfaces.

Automated browser and Axe checks are evidence for detectable interaction/accessibility problems, not proof of complete accessibility conformance. Manual keyboard, screen-reader, zoom/reflow, visual contrast/usability, multi-tab, prolonged network-interruption, target-network recovery, and inclusive-user acceptance remain separate acceptance work.

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
- `GET /api/v1/inbox/state` — authoritative user-scoped latest Delivery cursor and total/unread/acknowledged counts
- `GET /api/v1/inbox/stream` — session-authenticated SSE stream with persisted Delivery cursor/replay and aggregate-state events
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

Before controlled cutover, GoreeCloud Notify still requires the applicable target-environment evidence for runtime/private publication, backup/restore, monitoring, independent Notify-down alert delivery, real-time network behavior, and producer/consumer migration. No draft PR by itself authorizes DNS, Caddy, AdGuard Home, NetBird, firewall, Uptime Kuma, producer, subscriber, database, or ntfy retirement changes.

## Next roadmap

- **Milestone 3 acceptance:** manual browser/visual and accessibility review remains an independent acceptance activity for the Glaze interface.
- **Milestone 4:** continue from synchronized SSE delivery and explicit offline recovery into deliberate browser Notifications API permission/privacy behavior, followed by manual multi-tab/network acceptance.
- **Milestone 5:** Android client evaluation/implementation after web/API stability.
- **Milestone 6:** controlled ntfy migration with producer-by-producer validation and rollback.
- **Milestone 7:** GoreeCloud platform integrations.
- **Milestone 8:** iOS client after platform/signing/transport requirements are verified.

## License

The application license remains an open project decision. The repository remains private while the approved open-source license is selected and recorded.
