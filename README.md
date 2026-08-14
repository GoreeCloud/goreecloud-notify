# GoreeCloud Notify

GoreeCloud Notify is the planned GoreeCloud-native centralized notification-delivery service and long-term successor to ntfy.

> **Development status:** Milestone 2 development is stacked on the unmerged Milestone 1 foundation. GoreeCloud Notify is not deployed and does not replace the current ntfy service at `https://notify.goreecloud.com`.

## Current development scope

Milestone 1 establishes the FastAPI/React/SQLite/Docker/CI foundation.

Milestone 2 is currently split into focused stacked changes:

- PR #2: bootstrap admin authorization, service identities, scoped producer tokens, token revocation, sources, and channels.
- PR #3: native `POST /api/v1/notifications` ingestion, persistence through the existing Notification model, producer source-ownership enforcement, and focused tests.
- PR #4: producer-scoped notification history and detail access with `notifications:read`, source isolation, filters, and bounded cursor pagination.
- PR #5: initial ntfy-compatible POST/PUT topic publishing for authenticated producers, including simple message/title/priority translation and explicit rejection of unsupported ntfy features.
- PR #6: design-only human authentication and user-level Delivery read/unread/acknowledgement semantics.
- PR #7: administrator-provisioned human accounts, Argon2id credential hashes, opaque server-side web sessions, Alembic schema migrations, login/logout, and `GET /api/v1/me`.
- PR #8: subscription-based per-user `Delivery` fanout plus authenticated read-only `GET /api/v1/inbox` and delivery-detail access with strict user isolation and bounded filtering/pagination.
- PR #9: server-side synchronizer CSRF tokens plus owned Delivery read, unread, acknowledgement, and CSRF-protected logout mutations.

Native notification writes are enabled only in the pre-production development API and require a producer token with the `notifications:write` scope. Producer history requires `notifications:read` and only exposes notifications belonging to that service identity's sources. The compatibility adapter preserves GoreeCloud authentication and the current 4 KiB ntfy message-size boundary. Human login/session runtime is implemented on the pre-production PR #7 stack. PR #8 adds subscription-based user-level Delivery fanout and a read-only authenticated inbox. PR #9 adds session-bound synchronizer CSRF protection and owned Delivery read/unread/acknowledgement mutations. Real-time delivery and production migration remain unimplemented.

## Repository structure

```text
.
├── backend/              FastAPI API and SQLite model
├── frontend/             React + TypeScript + Vite web client
├── docs/                 Architecture, development, security, migration
├── docker-compose.yml    Isolated development topology
└── .github/workflows/    Continuous integration
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
npm install --ignore-scripts
npm run lint
npm run check
npm run build
npm run dev -- --host 127.0.0.1
```

Before Milestone 1 is merged, `frontend/package-lock.json` and reproducible `npm ci` remain an outstanding gate.

## Docker development

```bash
docker compose config
docker compose up --build
```

Development ports remain loopback-only: frontend `127.0.0.1:5173`, backend `127.0.0.1:8000`. This repository does not modify Caddy, AdGuard Home, NetBird, DNS, or the active ntfy deployment.

## API status

- `GET /healthz` — application/database health
- `GET /api/v1/meta` — development milestone/status metadata
- Milestone 2 administration endpoints are under `/api/v1`
- `POST /api/v1/notifications` — native scoped producer ingestion
- `GET /api/v1/notifications` — producer-scoped history with optional source/channel/severity filters and `before_id` pagination
- `GET /api/v1/notifications/{id}` — producer-scoped notification detail
- `POST|PUT /{topic}` — initial ntfy-compatible simple topic publishing for scoped producers
- `POST /api/v1/users` — administrator-provisioned human account creation
- `POST /api/v1/session` — human login with an opaque `HttpOnly` web session cookie
- `DELETE /api/v1/session` — CSRF-protected server-side session revocation/logout
- `GET /api/v1/csrf` — recover the current session-bound synchronizer token for the authenticated SPA
- `GET /api/v1/me` — current authenticated human profile
- `GET /api/v1/inbox` — authenticated user-owned Delivery history with read/acknowledgement/source/channel/severity filters and bounded pagination
- `GET /api/v1/inbox/{delivery_id}` — authenticated user-owned Delivery detail; other users' delivery IDs are hidden as not found
- `POST /api/v1/inbox/{delivery_id}/read` — CSRF-protected owned Delivery mark-read mutation
- `DELETE /api/v1/inbox/{delivery_id}/read` — CSRF-protected owned Delivery mark-unread mutation; acknowledgement is preserved
- `POST /api/v1/inbox/{delivery_id}/acknowledge` — CSRF-protected owned acknowledgement; acknowledgement also marks an unread Delivery read
- tags, actions, attachments, Markdown, delays, email, calls, and other advanced ntfy options are explicitly unsupported in the initial adapter rather than silently discarded

See `docs/notification-engine.md` for the current Milestone 2 boundary.

## License

The project license is intentionally **not selected yet** because the authoritative project specification records licensing as an open implementation decision. The repository should remain private until an approved open-source license is selected and recorded.
