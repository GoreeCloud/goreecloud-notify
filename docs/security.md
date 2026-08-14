# Security Boundaries

Milestone 1 deliberately has no notification write endpoint and no authentication token generation.

Current controls:

- no reusable secrets in source
- loopback-only development port publication
- non-root backend container user
- read-only container filesystems with explicit writable data/tmp locations
- all Linux capabilities dropped
- `no-new-privileges`
- SQLite persistent state outside the writable container layer
- narrow development CORS origins and GET-only method allowance
- no Docker socket access
- no Caddy, DNS, NetBird, ntfy, or production credential changes

Milestone 2 must add authenticated service identities, token hashing, explicit scopes, authorization, input validation, rate controls, and auditable administrative behavior before notification ingestion is enabled.
