# Changelog

All notable source releases of GoreeCloud Notify are recorded here. Detailed operational history remains in the authoritative GoreeCloud change-log records.

## Unreleased

### Changed

- Recorded Glaze UI 1.0.0 as the web application's explicit design-system target and added an application-level semantic contract for shared target sizing, focus, motion, radii, semantic roles, and adaptive ranges.
- Aligned the primary responsive transformations with Glaze UI Compact, Medium, Expanded, and Wide ranges while preserving Notify's established notification-focused composition.
- Replaced stale development-milestone presentation with release-aware version, stage, immutable build-revision, and production-acceptance status from `/api/v1/meta`.
- Updated product metadata and browser theme-color metadata for the private Notify application experience.
- Integrated Wardveil Security presentation metadata without changing the authority of the application's underlying security controls.
- Added privacy-minimized structured HTTP observability with bounded `X-Request-ID` correlation, route-template/status/duration events, generic correlated unexpected-error responses, and deliberate exclusion of request secrets and personal network/browser metadata.
- Added a unique canonical GoreeCloud Notify application icon and made the in-application product marks, web favicon, installable-web manifest, Linux AppImage identity contract, and Android APK identity contract converge on the same source artwork.
- Added a source-controlled application-identity contract so platform-specific launcher assets may adapt required padding, masking, monochrome behavior, or rasterization without creating a separate Notify identity.
- Added an explicit production serving contract for the canonical icon and installable-web manifest with bounded revalidating public cache policies and exact media types.
- Separated runtime environment/configuration metadata from immutable product release-stage and production-acceptance metadata so target-validation deployments cannot silently promote themselves merely by using production-mode settings.
- Added explicit pending acceptance-gate metadata for backup/restore, independent monitoring, target runtime/private publication, and manual browser/OS validation while preserving the existing `production` field as the production-configuration compatibility indicator.

### Fixed and hardened

- Browser system-alert permission state now observes supported Permissions API change events and retains focus, pageshow, and visibility reconciliation as compatibility fallbacks.
- Externally blocked browser notification permission now clears the local opt-in promptly and is visible in the collapsed settings summary instead of appearing as an unrequested permission.
- System-alert privacy remains explicit opt-in, foreground-suppressed, backlog-suppressed, and limited to generic redacted operating-system text.
- Actionable controls enforce the Glaze UI 44-pixel minimum target contract, with forced-colors and existing reduced-motion/transparency resilience preserved.
- Invalid caller-supplied request identifiers are replaced instead of being trusted as log correlation input.
- Unexpected server errors no longer require exposing raw exception text to the client; the generic response carries only a sanitized correlation identifier.
- Response hardening now additionally declares same-origin opener/resource isolation, origin-agent clustering, and denial of legacy cross-domain policy files.
- Replaced the visible generic `G` product placeholder treatment with the canonical Notify mark without adding a remote image, font, script, analytics, or tracking dependency.
- Fixed the production-runtime gap where Vite copied the canonical icon and `manifest.webmanifest` into the image but FastAPI exposed only `/assets/*` and `/`, causing the favicon and installable-web identity resources to be unavailable through the final application server.
- Restricted production identity delivery to the exact canonical icon and manifest routes rather than widening the runtime into a general-purpose public static-file tree; missing identity artifacts remain private, non-cacheable failures.
- Tightened cache classification so only successful immutable build assets or approved identity resources retain public caching while static-resource errors fall back to `no-store`/`no-cache` protection.
- Fixed `/api/v1/meta` incorrectly reporting `release_stage: production` solely because `GOREECLOUD_NOTIFY_ENVIRONMENT=production`; the current source line now remains explicitly `release_candidate` with production acceptance pending until a future accepted release intentionally changes source metadata.

### Validation

- Expanded Playwright coverage records the Glaze UI target, core semantic contract values, minimum actionable target size, release-candidate presentation, and Permissions API revocation reconciliation.
- Added backend regression coverage for Wardveil response metadata, generated and preserved request IDs, unsafe request-ID replacement, privacy-minimized structured log events, stronger browser-isolation headers, and secret-safe correlated unexpected-error handling.
- Added regression coverage for canonical icon safety, browser/installable-web metadata, visible product-mark usage, and cross-platform web/AppImage/APK icon-source consistency.
- Added runtime regression coverage for canonical icon/manifest status, media type, cache behavior, browser-security headers, private failure behavior, and denial of arbitrary `/brand/*` files.
- Extended the disposable production-readiness HTTPS client to prove the final Caddy/application topology can actually serve the manifest and canonical icon with the expected identity reference and cache/security contract.
- Added backend and production-readiness regression assertions that production-mode configuration remains distinct from release stage, acceptance state, and the four outstanding production-acceptance gates.
- Existing WCAG A/AA automation, Compact overflow checks, realtime/offline recovery, multi-tab behavior, and production/disposable readiness gates remain part of the pull-request validation set.

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
