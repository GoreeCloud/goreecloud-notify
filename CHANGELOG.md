# Changelog

All notable source releases of GoreeCloud Notify are recorded here. Detailed operational history remains in the authoritative GoreeCloud change-log records.

## 0.2.0 — Release candidate

### Added

- FastAPI notification service with SQLite/SQLAlchemy persistence and Alembic migrations.
- Scoped producer identities, tokens, sources, channels, native ingestion, producer history, and an initial ntfy-compatible publishing path.
- Human users, Argon2id passwords, opaque server-side sessions, CSRF protection, administrator authorization/audit, login abuse controls, and administrator password reset.
- User subscriptions, Delivery fanout, authenticated inbox history/detail, read/unread state, acknowledgement, search, filtering, and cursor pagination.
- Glaze UI authenticated inbox with responsive system/light/dark appearance, subscription management, accessibility-oriented interaction, and privacy-first browser system alerts.
- Authenticated Server-Sent Events with persisted replay cursors, authoritative inbox state, reconnect/offline recovery, multi-tab reconciliation protections, and long-lived session revalidation.
- SQLite Online Backup API recovery tooling, integrity/foreign-key/Alembic verification, restored-session invalidation, and alternate-location synthetic restore validation.
- Reproducible multi-stage production image, non-root/read-only Compose runtime, external proxy-network publication model, production configuration template, private Caddy contract, monitoring readiness, and read-only target preflight tooling.
- Deterministic Python/npm dependency-license inventory, response privacy headers, browser isolation policy, immutable build-revision metadata, and pinned CI/runtime baselines.
- MIT application license and OCI source/version/license metadata.
- Guarded manual GitHub Actions source-prerelease publication for `v0.2.0`, restricted to an exact current-main commit SHA and verified after publication.

### Fixed and hardened

- Fail-closed security-sensitive configuration parsing and session timing validation.
- SQLite foreign-key enforcement and UTC timestamp canonicalization.
- Required administrative-name and notification-title normalization.
- Inactive-user session revocation persistence.
- Realtime/REST ordering and reconnect races.
- Auto/System Glaze appearance on light operating-system themes.
- Browser preference behavior when local storage is unavailable.
- Browser-alert state changes no longer restart the realtime SSE transport.
- Production Compose now requires the immutable Git build revision and propagates it to both application and migration image builds, preventing production-tagged images from retaining the `development` revision fallback.
- Production HTTPS publication adds one-year HSTS without `includeSubDomains` or preload expansion, and both disposable readiness and real target preflight tooling verify the HSTS response contract.

### Validation

The final source line passed backend regression tests, locked frontend lint/type/build validation, Chromium/browser-accessibility tests, production-readiness validation, monitoring-alert readiness, dependency/license verification, and target-preflight self-tests. The production-readiness gate additionally proves fail-closed build-revision handling, exact revision propagation, HSTS, private-network authorization, persistence, and synthetic secret-leak protections.

Production activation remains a separate controlled operation. ntfy remains the active production notification service until target backup/restore, monitoring/out-of-band alerting, private-publication/runtime, manual browser/OS acceptance, migration, and rollback evidence are complete.
