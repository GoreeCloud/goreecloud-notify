# GoreeCloud Notify Release Checklist

This checklist distinguishes source-release readiness from production activation.

## Source release

- [x] Milestones 1–4 source implementation complete for the current web/API scope.
- [x] Required authentication/authorization/input/database hardening integrated.
- [x] Reproducible frontend lock/install/build path.
- [x] Reproducible constrained backend dependency closure.
- [x] Production multi-stage image and least-privilege runtime contract.
- [x] Private-publication source contract and disposable Production readiness gate.
- [x] Monitoring source contract and disposable DOWN/RECOVERED readiness gate.
- [x] Application-specific SQLite backup/restore tooling and synthetic alternate-location restore validation.
- [x] Immutable Git build-revision identity.
- [x] Response privacy and browser-isolation security headers.
- [x] Browser/accessibility automation.
- [x] Glaze UI system/light/dark appearance resilience.
- [x] Browser preference/storage resilience and stream-stable system-alert state.
- [x] MIT license applied and included in the production image.
- [x] Release README, changelog, deployment runbook, and dependency-license review.
- [x] Final integration PR exact-head CI/browser/Production readiness/Monitoring alert readiness green — PR #61 head `b96b23eea57fc6bcb69147ac28671b749b72e38b`.
- [x] Main-branch post-merge validation green — authoritative merge commit `34aa4625c00254cf185d74ba8b366daf734813ef`, CI run `31964946420`, Browser accessibility run `31964946419`.
- [ ] Version tag/release created from the accepted main commit. The connected GitHub tool surface does not currently expose a create-tag/GitHub-Release action; do not claim a tag exists until one is intentionally created and verified.

## Manual browser/OS acceptance

- [ ] Keyboard/focus acceptance.
- [ ] Screen-reader acceptance.
- [ ] Zoom/reflow and practical visual/contrast acceptance.
- [ ] Real multi-tab realtime acceptance.
- [ ] Browser permission grant/deny/revoke acceptance.
- [ ] Actual OS notification privacy/redaction acceptance.
- [ ] Reconnect/backlog duplicate-alert acceptance.

Tracked by issue #55.

## Target runtime/private publication

- [ ] Candidate deployed on approved target host.
- [ ] Target runtime/filesystem/secret-file evidence passes.
- [ ] Private DNS/TLS/Caddy/NetBird approved-source behavior passes.
- [ ] Unauthorized-source behavior passes.
- [ ] Long-lived SSE/session revocation/expiry through final Caddy path passes.
- [ ] Prolonged real-network interruption/recovery passes.

Tracked by issue #25.

## Target backup/recovery

- [ ] Backup repository/destination approved.
- [ ] Backup frequency/RPO approved.
- [ ] Recovery-point retention approved.
- [ ] Independent failed/missed-backup monitoring configured.
- [ ] Target backup verified.
- [ ] Alternate-location target application restore passes and observed recovery time is recorded.

Tracked by issue #23.

## Target monitoring/outage alerting

- [ ] Final private HTTPS Uptime Kuma monitor registered.
- [ ] Healthy/no-alert behavior verified.
- [ ] Controlled DOWN and RECOVERED sequence verified.
- [ ] Administrator receipt verified.
- [ ] Independent Notify-down alert path deployed and tested.

Tracked by issue #24.

## Migration and rollback

- [ ] Producer inventory reconciled.
- [ ] Consumer/subscription inventory reconciled.
- [ ] Producers migrated incrementally with delivery verification.
- [ ] Final hostname cutover validated.
- [ ] ntfy rollback tested and retained through the approved rollback window.
- [ ] ntfy retirement separately approved.

Production is not considered complete until every applicable unchecked target/manual item above has evidence tied to the exact deployed build.
