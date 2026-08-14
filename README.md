# GoreeCloud Notify

GoreeCloud Notify is the planned GoreeCloud-native centralized notification-delivery service and long-term successor to ntfy.

> **Development status:** Milestone 1 foundation. GoreeCloud Notify is not deployed and does not replace the current ntfy service at `https://notify.goreecloud.com`.

## Milestone 1 scope

This foundation establishes:

- FastAPI backend skeleton
- React + TypeScript + Vite frontend skeleton
- SQLite/SQLAlchemy first-class data model
- health and metadata endpoints
- Docker Compose development environment
- backend tests and frontend type/build validation
- GitHub Actions CI
- security, architecture, migration, and development documentation

Notification publishing, scoped service tokens, ntfy-compatible ingestion, real-time delivery, mobile clients, and production migration belong to later milestones.

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

Before Milestone 1 is merged, generate and commit `frontend/package-lock.json` with `npm install --package-lock-only`, then change CI and the frontend Dockerfile to `npm ci`. The scaffold keeps exact direct dependency versions while that lockfile is pending.

## Docker development

```bash
docker compose config
docker compose up --build
```

The development Compose file publishes only loopback ports:

- frontend: `127.0.0.1:5173`
- backend: `127.0.0.1:8000`

It does not modify Caddy, AdGuard Home, NetBird, DNS, or the active ntfy deployment.

## API foundation

- `GET /healthz` — application/database health
- `GET /api/v1/meta` — Milestone 1 API metadata and entity inventory

The notification write API is intentionally not implemented in Milestone 1.

## License

The project license is intentionally **not selected yet** because the authoritative project specification records licensing as an open implementation decision. The repository should remain private until an approved open-source license is selected and recorded.
