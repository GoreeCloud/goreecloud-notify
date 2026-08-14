# GoreeCloud Notify

GoreeCloud Notify is the original GoreeCloud-owned centralized notification-delivery application being developed as the long-term successor to ntfy.

> **Development status:** Milestone 3 Glaze UI Inbox development is stacked on the unmerged Milestone 2 and production-readiness work. GoreeCloud Notify is not deployed and does not replace the current ntfy service at `https://notify.goreecloud.com`.

## Current development scope

The repository now contains three major development layers:

1. **Milestone 1 foundation** — FastAPI, React/TypeScript/Vite, SQLite/SQLAlchemy, Docker development topology, documentation, tests, and GitHub Actions.
2. **Milestone 2 notification engine** — producer identities and scoped tokens, sources/channels, native and initial ntfy-compatible ingestion, persistence, producer history, administrator-provisioned human users, opaque web sessions, subscription fanout, user-owned inbox state, CSRF protection, subscription administration, and non-destructive retention analysis.
3. **Milestone 3 Glaze UI Inbox** — authenticated web sign-in, session restoration, notification-center layout, inbox summary, search and filters, source/severity presentation, notification detail, read/unread and acknowledgement actions, responsive behavior, accessibility controls, and system/light/dark appearance selection.

The stacked hardening/readiness line also includes fail-closed session configuration, SQLite foreign-key enforcement, UTC datetime canonicalization, production administrator authorization, login abuse controls, administrator password reset, required-text normalization, backup/restore tooling and recovery validation, production runtime/private-publication readiness, and monitoring/outage-alert readiness.

All of those changes remain draft and pre-production until intentionally integrated.

## Milestone 3 web experience

The Milestone 3 inbox uses the existing security contracts rather than creating a separate frontend authentication model.

- `POST /api/v1/session` creates the HttpOnly human session and returns the session-bound CSRF token header.
- `GET /api/v1/me` restores an existing authenticated browser session.
- `GET /api/v1/csrf` restores the current CSRF token when a browser session already exists.
- `GET /api/v1/inbox?limit=100` supplies the current bounded working set for the first Glaze UI inbox slice.
- Search and the first source/severity/read filters operate locally over that bounded working set; server-side filtering and cursor pagination remain available in the API for later UI refinement.
- Read, unread, acknowledgement, and logout mutations send the existing `X-CSRF-Token` protection.
- Browser requests use `credentials: include`, which preserves the production same-origin model while allowing the separate local Vite origin to use the existing development CORS configuration.
- Theme preference is presentation-only browser state stored in local storage; it is not an authentication or server preference record.

The UI does not display producer tokens, session-cookie values, CSRF values, database configuration, or other reusable credentials.

## Repository structure

```text
.
├── backend/                    FastAPI API, SQLite model, migrations, recovery tooling
├── frontend/                   React + TypeScript + Vite web client
├── deploy/                     Proposed production/private-publication and monitoring contracts
├── docs/                       Architecture, security, recovery, monitoring, migration
├── docker-compose.yml          Isolated development topology
├── Dockerfile.production       Production multi-stage frontend/backend image
└── .github/workflows/          CI and source-controlled readiness gates
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
- `GET /api/v1/inbox` — user-owned Delivery history with filters and cursor pagination
- `GET /api/v1/inbox/{delivery_id}` — user-owned Delivery detail
- `POST /api/v1/inbox/{delivery_id}/read` — mark read
- `DELETE /api/v1/inbox/{delivery_id}/read` — mark unread
- `POST /api/v1/inbox/{delivery_id}/acknowledge` — acknowledge and mark read
- `GET /api/v1/subscriptions` — current user's channel subscription state
- `PUT|DELETE /api/v1/subscriptions/{channel_slug}` — CSRF-protected subscription changes

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

- **Milestone 3:** continue Glaze UI inbox interaction/accessibility refinement and bounded pagination/subscription experience work.
- **Milestone 4:** real-time WebSocket and/or SSE delivery, reconnect behavior, unread counters, and browser notification support where approved.
- **Milestone 5:** Android client evaluation/implementation after web/API stability.
- **Milestone 6:** controlled ntfy migration with producer-by-producer validation and rollback.
- **Milestone 7:** GoreeCloud platform integrations.
- **Milestone 8:** iOS client after platform/signing/transport requirements are verified.

## License

The application license remains an open project decision. The repository remains private while the approved open-source license is selected and recorded.
