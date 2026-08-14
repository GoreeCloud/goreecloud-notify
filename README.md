# GoreeCloud Notify

GoreeCloud Notify is the planned GoreeCloud-native centralized notification-delivery service and long-term successor to ntfy.

> **Development status:** Milestone 2 development is stacked on the unmerged Milestone 1 foundation. GoreeCloud Notify is not deployed and does not replace the current ntfy service at `https://notify.goreecloud.com`.

## Current development scope

Milestone 1 establishes the FastAPI/React/SQLite/Docker/CI foundation.

Milestone 2 is currently split into focused stacked changes:

- PR #2: bootstrap admin authorization, service identities, scoped producer tokens, token revocation, sources, and channels.
- PR #3: native `POST /api/v1/notifications` ingestion, persistence through the existing Notification model, producer source-ownership enforcement, and focused tests.

Native notification writes are enabled only in the pre-production development API and require a producer token with the `notifications:write` scope. ntfy-compatible ingestion, user delivery/read/acknowledgement state, and production migration remain unimplemented.

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
- `POST /api/v1/notifications` — native scoped producer ingestion on the PR #3 development stack
- ntfy-compatible topic ingestion is not implemented yet

See `docs/notification-engine.md` for the current Milestone 2 boundary.

## License

The project license is intentionally **not selected yet** because the authoritative project specification records licensing as an open implementation decision. The repository should remain private until an approved open-source license is selected and recorded.
