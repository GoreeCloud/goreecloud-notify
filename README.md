# GoreeCloud Notify

GoreeCloud Notify is the original GoreeCloud-owned centralized notification-delivery application being developed as the long-term successor to ntfy.

> **Development status:** Milestone 4 real-time delivery source development is now focused on acceptance and stabilization. The entire stack remains draft, unmerged, and pre-production. GoreeCloud Notify is not deployed and does not replace the current ntfy service at `https://notify.goreecloud.com`.

## Current development scope

The repository contains four major development layers:

1. **Milestone 1 foundation** — FastAPI, React/TypeScript/Vite, SQLite/SQLAlchemy, Docker development topology, documentation, tests, and GitHub Actions.
2. **Milestone 2 notification engine** — producer identities and scoped tokens, sources/channels, native and initial ntfy-compatible ingestion, persistence, producer history, administrator-provisioned human users, opaque web sessions, subscription fanout, user-owned inbox state, CSRF protection, subscription administration, and non-destructive retention analysis.
3. **Milestone 3 Glaze UI Inbox** — authenticated web sign-in, session restoration, notification-center layout, server-backed search/filters, cursor pagination, user-owned channel subscription management, source/severity presentation, notification detail, read/unread and acknowledgement actions, fail-visible logout behavior, responsive accessibility controls, system/light/dark appearance selection, Chromium interaction validation, and automated WCAG A/AA checks.
4. **Milestone 4 real-time delivery** — authenticated Server-Sent Events, persisted Delivery cursors, replay semantics, long-lived session revalidation, authoritative inbox aggregate state, cursor-bootstrap synchronization, native EventSource integration, reconnect/offline recovery, privacy-first browser system alerts, and reconciliation protections that prevent stale REST responses from erasing newer realtime Deliveries.

The stacked hardening/readiness line also includes fail-closed session configuration, SQLite foreign-key enforcement, UTC datetime canonicalization, production administrator authorization, login abuse controls, administrator password reset, required-text normalization, backup/restore tooling and recovery validation, production runtime/private-publication readiness, and monitoring/outage-alert readiness.

All of these changes remain draft and pre-production until intentionally integrated.

## Human sessions and Glaze inbox

The Glaze inbox uses the existing backend security contracts rather than creating separate frontend authentication or authorization models.

- `POST /api/v1/session` creates an HttpOnly human session and returns the session-bound CSRF token header.
- `GET /api/v1/me` restores an authenticated browser session.
- `GET /api/v1/csrf` restores the current session-bound CSRF token.
- `GET /api/v1/inbox` returns a bounded user-owned Delivery page and accepts read/source/channel/severity/search/cursor filters.
- `q` performs case-insensitive user-scoped search across notification title/body plus source and channel names/slugs; SQL LIKE wildcard characters supplied by the user are escaped and treated literally.
- The web client debounces search, composes server-backed filters, cancels stale filter requests, and loads older results with `before_id`.
- `GET /api/v1/subscriptions` supplies the authenticated user's state for all available notification channels.
- `PUT` and `DELETE /api/v1/subscriptions/{channel_slug}` are CSRF-protected and modify future fanout without deleting existing Delivery history.
- Read, unread, acknowledgement, subscription, and logout mutations use the existing session-bound CSRF protection.
- Browser API requests use `credentials: include`, preserving the production same-origin model while supporting the separate local Vite development origin.
- A logout request that cannot confirm server-side revocation leaves the authenticated UI active and reports the error instead of falsely reporting a successful sign-out.
- Theme preference and browser system-alert preference are browser-local presentation preferences, not authentication records.

The UI does not display producer tokens, session-cookie values, CSRF values, database configuration, or other reusable credentials.

## Milestone 4 real-time delivery

Milestone 4 currently uses Server-Sent Events because the web requirement is one-way server-to-browser notification delivery. A WebSocket dependency is not added merely for transport symmetry.

### Server stream contract

`GET /api/v1/inbox/stream` provides the authenticated user's real-time Delivery stream.

- Authentication uses the existing HttpOnly human-session cookie. Producer bearer tokens are not accepted as a substitute for a human session.
- Authentication completes in a short-lived SQLAlchemy session before the long-lived `StreamingResponse` starts.
- The stream is isolated by `Delivery.user_id`.
- Delivery state is read from persisted SQLite data instead of process-local pub/sub state.
- Each `inbox` event uses the Delivery ID as the SSE event ID and carries the existing `InboxDeliveryRead` representation.
- `after_id` explicitly requests replay after a non-negative Delivery ID.
- `Last-Event-ID`, when supplied by the SSE client, takes precedence over `after_id`; malformed or negative values fail with HTTP 400.
- The server advertises a 3-second SSE retry interval and emits periodic keepalive comments.
- The backing `WebSession` is revalidated while the stream remains open. Session revocation, password-reset invalidation, user deactivation, absolute expiry, or idle expiry terminates continued authorization.
- Streaming responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

Central Caddy remains the intended HTTPS gateway. The design does not add a separate public listener or second application gateway for SSE.

### Authoritative inbox state

`GET /api/v1/inbox/state` returns one user-scoped synchronization snapshot:

- `latest_delivery_id` — newest owned persisted Delivery ID, or `0` for an empty inbox;
- `total_count` — total owned Delivery count;
- `unread_count` — total owned Deliveries where `read_at` is unset;
- `acknowledged_count` — total owned Deliveries where `acknowledged_at` is set.

The values are calculated server-side in one user-scoped aggregate query. The Glaze UI therefore does not present a loaded 50-item page count as if it were the user's authoritative total state.

The SSE `ready` event carries the same authoritative state with the active replay cursor. The stream also emits `state` events when aggregate state changes, including read or acknowledgement activity from another client that does not create a new Delivery.

### Cursor-bootstrap synchronization

The browser establishes the realtime connection in this order:

1. restore the authenticated session;
2. load `GET /api/v1/inbox/state` and retain `latest_delivery_id` as the initial stream cursor;
3. load/render the normal server-backed inbox page independently;
4. open EventSource with `after_id=<snapshot latest_delivery_id>`;
5. accept Delivery/state events only after a valid `ready` synchronization snapshot;
6. reconcile the normal REST inbox after every valid `ready` event.

This closes the ordinary race where a Delivery can be created between the initial REST load and realtime attachment. The bootstrap cursor is not advanced from aggregate state after startup; reconnect and offline-recovery correctness uses Delivery IDs the browser has actually processed.

### Realtime and REST reconciliation

A realtime Delivery can arrive while a REST inbox reconciliation request is already in flight. The client protects against an older REST response erasing that newer live Delivery.

- Each realtime Delivery inserted into the current simple-filter view is marked as pending reconciliation by Delivery ID.
- A later REST response replaces or absorbs that pending Delivery only when the server response actually contains the same Delivery ID.
- Pending realtime Deliveries missing from an older REST response remain visible when they still satisfy the current view.
- Text-search views remain server-owned; realtime events trigger server reconciliation rather than attempting to duplicate search semantics in browser code.
- Read/unread/acknowledgement mutations refresh authoritative aggregate state and immediately reconcile the active filtered view.

This protection was added after browser validation exposed a real ordering race between stream delivery and post-handshake REST refresh.

### Explicit offline recovery

The Glaze inbox reports connecting, live, reconnecting, offline, or idle state through an accessible status region.

- `offline` is used only when the browser reports `navigator.onLine === false`.
- If the browser reports online but Notify is unreachable, EventSource failure remains `reconnecting` rather than being mislabeled offline.
- While explicitly offline, the hook does not keep or create an EventSource and the UI states that loaded results are stale until network recovery.
- While reconnecting with browser connectivity available, the client periodically revalidates `GET /api/v1/me`; HTTP 401 clears the authenticated UI.
- After a transport error or explicit restart, Delivery/state events are ignored until a new valid `ready` event re-establishes synchronization.
- The explicit recovery cursor advances only after a valid Delivery has actually been processed by the browser.
- Aggregate `latest_delivery_id` does not advance the recovery cursor because it could move the boundary past a Delivery the browser has not consumed.
- When connectivity returns, the hook creates a fresh EventSource using `after_id=<last processed Delivery ID>`, accepts replay only after a new valid `ready`, and reconciles the REST inbox after synchronization.

## Privacy-first browser system alerts

Browser system alerts are an optional convenience layer over the protected Notify inbox. They are intentionally privacy-limited.

### Permission and preference behavior

- System alerts are **off by default**.
- The application never calls `Notification.requestPermission()` during page load, session restoration, stream startup, or background initialization.
- Permission can be requested only after the user explicitly selects **Enable system alerts** in the Glaze settings disclosure.
- The app-level enabled/disabled preference is stored locally in the current browser.
- Browser site permission remains browser-controlled. If permission becomes denied or otherwise ceases to be granted, Notify disables its local enabled state when permission is re-synchronized.
- The settings surface distinguishes unsupported, not-requested, browser-granted/app-off, locally enabled, and browser-denied states.

### Privacy content rule

Operating-system alerts use fixed generic content:

- title: `GoreeCloud Notify`
- body: `A new notification is available. Open Notify to view details.`

By default the OS alert does **not** include the Delivery title, body, source, channel, account name, Delivery ID, or other notification detail. The authenticated Notify inbox remains the protected surface for inspecting the event.

### Visibility and replay behavior

- A system alert is eligible only when Notify is open and the document is hidden.
- Foreground/visible-page Deliveries remain in the Glaze inbox without creating an OS alert.
- No service worker, Web Push subscription, push server, page-closed delivery, or mobile push claim is implemented in this slice.
- Every valid `ready` event establishes the browser-alert baseline.
- Every processed Delivery advances the browser-alert baseline even if alerts are disabled or the page is visible.
- Replay/backlog Deliveries at or below the synchronization baseline do not generate an alert storm after reconnect, offline recovery, or later opt-in.

## Browser and accessibility validation

The frontend has a separate read-only GitHub Actions browser gate using locked Playwright and Axe dependencies. It builds the immutable Vite artifact and validates isolated Chromium scenarios against synthetic API/stream contracts.

Current automated evidence covers:

- authenticated inbox rendering and semantic navigation;
- native EventSource Delivery parsing;
- authoritative `after_id` bootstrap and total/unread/read counts;
- live/reconnecting/offline transport state;
- forced Chromium offline state and explicit stale-data presentation;
- online recovery from the last processed Delivery cursor;
- immediate filtered reconciliation after read mutations;
- protection against older REST reconciliation erasing newer realtime Deliveries;
- no automatic browser notification permission request;
- exactly one permission request after explicit opt-in in the privacy test harness;
- generic/redacted OS notification content;
- rejection of synthetic private title/body/source/channel leakage into the OS alert;
- hidden-page alert behavior and foreground alert suppression;
- replay/backlog system-alert suppression;
- keyboard skip-link discovery;
- server-backed unread filtering and debounced search;
- cursor-based `Load more` behavior;
- subscription interaction with CSRF validation;
- dark-mode state;
- narrow mobile rendering without horizontal document overflow;
- sign-in form labels and controls;
- automated Axe analysis for selected WCAG A/AA rule tags on authenticated and unauthenticated surfaces.

Automated browser and Axe checks are evidence for detectable problems, not proof of complete accessibility, privacy, or real-network conformance.

## Acceptance and stable-version boundary

The source feature work for the current Milestone 4 web slice is now at an acceptance boundary. Before treating GoreeCloud Notify as stable or preparing production migration, remaining evidence includes:

- manual full keyboard traversal and focus-order review;
- screen-reader behavior and announcements;
- browser zoom/reflow and visual contrast/usability review;
- manual multi-tab realtime behavior;
- prolonged real network interruption and recovery;
- browser system-alert grant, deny, disable, and externally revoked-permission behavior in real supported browsers;
- verification that real OS notification surfaces preserve the redacted content policy;
- target-environment central Caddy SSE behavior and session revocation during a live stream;
- target backup/restore, monitoring, independent Notify-down alerting, runtime/private-publication, and migration evidence;
- controlled producer/consumer migration with ntfy retained as rollback until cutover is intentionally approved.

No draft PR by itself satisfies those target-environment or manual acceptance requirements.

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

`frontend/package-lock.json` is committed and CI/release installs use the reproducible lock with `npm ci`.

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
- `GET /api/v1/inbox` — user-owned Delivery history with `read`, `acknowledged`, `source`, `channel`, `severity`, `q`, `before_id`, and bounded `limit` controls
- `GET /api/v1/inbox/state` — authoritative user-scoped latest Delivery cursor and total/unread/acknowledged counts
- `GET /api/v1/inbox/stream` — session-authenticated SSE stream with persisted Delivery cursor/replay and aggregate-state events
- `GET /api/v1/inbox/{delivery_id}` — user-owned Delivery detail
- `POST /api/v1/inbox/{delivery_id}/read` — mark read
- `DELETE /api/v1/inbox/{delivery_id}/read` — mark unread
- `POST /api/v1/inbox/{delivery_id}/acknowledge` — acknowledge and mark read
- `GET /api/v1/subscriptions` — all available channels plus current-user subscription state
- `PUT /api/v1/subscriptions/{channel_slug}` — CSRF-protected idempotent subscribe/resubscribe
- `DELETE /api/v1/subscriptions/{channel_slug}` — CSRF-protected idempotent unsubscribe without deleting historical deliveries

### Producers and compatibility

- `POST /api/v1/notifications` — native scoped producer ingestion
- `GET /api/v1/notifications` — producer-scoped history
- `GET /api/v1/notifications/{id}` — producer-scoped detail
- `POST|PUT /{topic}` — initial authenticated ntfy-compatible publishing

Advanced ntfy features such as attachments, delayed delivery, email/calls, actions, and broader formatting semantics remain outside the implemented compatibility boundary unless separately approved.

## Production and migration boundary

ntfy remains the active production notification service and rollback path. Draft source-level readiness work does **not** constitute a production deployment.

Before controlled cutover, GoreeCloud Notify still requires applicable target-environment evidence for runtime/private publication, backup/restore, monitoring, independent Notify-down alert delivery, real-time network behavior, browser notification behavior where used, and producer/consumer migration. No draft PR authorizes DNS, Caddy, AdGuard Home, NetBird, firewall, Uptime Kuma, producer, subscriber, database, or ntfy retirement changes.

## Next roadmap

- **Milestone 3 acceptance:** complete manual browser/visual/accessibility acceptance of the Glaze interface.
- **Milestone 4 acceptance:** complete manual realtime, multi-tab, network-recovery, and browser-system-alert privacy acceptance plus target-network evidence.
- **Milestone 5:** Android client evaluation/implementation after web/API stability.
- **Milestone 6:** controlled ntfy migration with producer-by-producer validation and rollback.
- **Milestone 7:** GoreeCloud platform integrations.
- **Milestone 8:** iOS client after platform/signing/transport requirements are verified.

## License

The application license remains an open project decision. The repository remains private while the approved open-source license is selected and recorded.
