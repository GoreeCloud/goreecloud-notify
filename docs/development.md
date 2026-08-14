# Development

## Backend quality gate

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest
```

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

The Compose topology is development-only and must not be treated as production approval.

## Dependency-lock gate

Before the Milestone 1 pull request is merged, generate `frontend/package-lock.json`, validate it with `npm ci`, and switch the frontend Dockerfile and CI install steps from `npm install` to `npm ci`.
