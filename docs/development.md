# Development

## Backend quality gate

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
alembic -c alembic.ini upgrade head
pytest
```

The application now verifies that the authentication-era schema exists at startup rather than silently using `create_all()` as a migration mechanism. Alembic is authoritative for persistent development databases.

For an old pre-Alembic **development-only** database created by the earlier scaffold, the safest path is to back it up and recreate it with `alembic upgrade head`. If temporary development records must be preserved, verify that it is exactly the pre-auth Milestone 2 schema, then stamp `0001_milestone_2_baseline` before upgrading to `head`. Never stamp an unknown production database merely to bypass a migration failure.

## Human-authentication development defaults

Human accounts are administrator-provisioned through `POST /api/v1/users`; public self-registration is not implemented. Passwords are stored only as Argon2id hashes. Web session tokens are opaque and only their SHA-256 digests are stored.

Development session defaults are configurable with:

- `GOREECLOUD_NOTIFY_SESSION_COOKIE_SECURE=false`
- `GOREECLOUD_NOTIFY_SESSION_LIFETIME_MINUTES=720`
- `GOREECLOUD_NOTIFY_SESSION_IDLE_MINUTES=60`
- `GOREECLOUD_NOTIFY_SESSION_TOUCH_MINUTES=5`

A deployed HTTPS environment must set `GOREECLOUD_NOTIFY_SESSION_COOKIE_SECURE=true`. The cookie is `HttpOnly` and `SameSite=Strict`. PR #9 uses a server-side synchronizer CSRF token for cookie-authenticated state changes: login returns `X-CSRF-Token`, `GET /api/v1/csrf` recovers it for the authenticated SPA, and mutation requests send it back in the `X-CSRF-Token` header. The token is session-bound server state, not a second authentication credential.

### PR #9 migration behavior

`0003_csrf_delivery_mutations` adds the per-session CSRF token. During upgrade it revokes every existing pre-CSRF web session. This is intentional: after upgrading to PR #9, human users must log in again so no session created under the previous security contract can perform protected mutations.

The migration is schema-compatible with SQLite through Alembic batch operations, and no manual session-row edits should be used to bypass the forced re-login boundary.

## Frontend quality gate

```bash
cd frontend
npm install --ignore-scripts
npm run lint
npm run check
npm run build
```

## Compose quality gate

```bash
docker compose config
docker compose up --build
curl --fail http://127.0.0.1:8000/healthz
```

The backend image runs `alembic upgrade head` before Uvicorn. The Compose topology is development-only and must not be treated as production approval.

## Dependency-lock gate

Before the Milestone 1 pull request is merged, generate `frontend/package-lock.json`, validate it with `npm ci`, and switch the frontend Dockerfile and CI install steps from `npm install` to `npm ci`.
