# Architecture

## Current milestone

Milestone 1 establishes the application foundation only. ntfy remains the active production notification service.

## Components

```text
Browser
  │
  ├── React + TypeScript + Vite frontend
  │
  └── FastAPI backend
        │
        └── SQLAlchemy
              │
              └── SQLite
```

Production publication is intentionally absent. A future approved deployment will follow the existing GoreeCloud private web-service model with Caddy, AdGuard Home, and NetBird.

## First-class entities

- User
- Device
- ServiceIdentity
- Source
- Channel
- Subscription
- Notification
- Delivery
- AccessToken
- Preference

The schema is a foundation, not a frozen production contract. Alembic migrations and final constraints should be introduced before schema changes become operationally significant.
