# GoreeCloud Notify Milestone 4 Acceptance and Stabilization Record

## Purpose

I use this record to define the evidence I require before I treat the current GoreeCloud Notify Milestone 4 web implementation as a stable production product and authorize controlled migration away from ntfy.

This record does not approve production deployment or ntfy replacement. The source line is integrated on `main`, the `v0.2.0` source release is a prerelease/release candidate, and post-release hardening continues on `main`. ntfy remains the current production notification service and rollback path until the remaining production-acceptance gates are completed and cutover is explicitly approved.

## Stabilization state

I am treating the current source line as an acceptance and stabilization checkpoint rather than a feature-development checkpoint.

I will not classify the current web implementation as stable merely because automated tests pass or because a runtime uses production-mode security configuration. I require source-controlled validation, manual browser/accessibility acceptance, target-environment evidence, recovery evidence, monitoring evidence, coherent same-candidate acceptance, and controlled migration evidence appropriate to the change being approved.

The runtime environment and product release state are separate concepts. `GOREECLOUD_NOTIFY_ENVIRONMENT=production` means the process is using the fail-closed production configuration contract; it does not mean production acceptance has completed. `/api/v1/meta` therefore reports the runtime environment/configuration independently from the immutable source release stage and production-acceptance state.

For the current source line the authoritative application metadata remains:

- release stage: `release_candidate`;
- production accepted: `false`;
- acceptance status: `pending`;
- backup/restore target evidence: pending;
- independent monitoring/out-of-band evidence: pending;
- target runtime/private-publication evidence: pending;
- manual browser/OS acceptance: pending.

A future Stable/production-accepted release must intentionally change the source release metadata after the required evidence is complete. Merely deploying this source with production configuration must never promote its user-facing release label automatically.

## Source-controlled automated evidence

The browser gate now exercises the following acceptance behavior with synthetic, isolated API and SSE contracts:

- I verify that two authenticated browser tabs can independently establish realtime streams from the same persisted Delivery cursor.
- I verify that both tabs retain the same user-owned realtime Delivery without one tab erasing the other tab's state.
- I verify that notification selection remains independent per tab rather than a realtime event forcing another tab's detail selection.
- I verify that a reconnecting browser revalidates the human session and clears authenticated UI when `/api/v1/me` reports HTTP 401 after revocation.
- I verify that browser notification permission is never requested automatically.
- I verify that explicit permission denial leaves system alerts disabled and does not persist the browser-local opt-in.
- I verify that externally revoked browser permission removes the browser-local enabled preference when permission state is re-synchronized.
- I verify that approved system alerts use fixed generic content and do not expose synthetic Delivery title, body, source, or channel data.
- I verify hidden-page alert eligibility, foreground suppression, and replay/backlog suppression.
- I verify synchronized SSE cursor bootstrap, authoritative aggregate counts, offline recovery, filtered REST reconciliation, subscription CSRF behavior, and responsive browser behavior.
- I run Axe checks for the configured WCAG A/AA rule tags on authenticated and unauthenticated surfaces.

The ordinary CI gate separately verifies backend regression tests and locked frontend lint, TypeScript, and build checks. Production-readiness and monitoring-readiness workflows continue to verify the disposable source-controlled deployment and outage-alert contracts. Production readiness also verifies that a production-configured runtime still identifies the current product as a release candidate with production acceptance pending and the exact immutable build revision intact.

## Manual evidence integrity workflow

The repository defines the issue #55 manual acceptance contract in `deploy/acceptance/manual_browser_os_acceptance.json` and validates completed sanitized evidence with `deploy/acceptance/validate_manual_browser_evidence.py`. The validator does not simulate or replace a human acceptance session. It verifies that the recorded evidence is complete, bound to one exact HTTPS candidate and Git revision, tied to real browser/OS/viewport session metadata, contains all required issue #55 checks, links failures to dedicated defects, and preserves the synthetic-data/privacy boundary.

The permanent GoreeCloud Notify records contain a substantial August 18, 2026 Firefox/Zorin OS candidate session against the frozen `v0.2.0` source. I treat that as historical acceptance evidence, not as a reconstructed passing bundle for the current source line. The record explicitly identifies remaining gaps in that capture, including enabled-alert replay/backlog no-alert-storm proof, exact viewport evidence, explicit Auto/Light/Dark confirmation, logout/login round-trip evidence, and separate sidebar Unread/Read filter confirmation. Later post-`v0.2.0` source hardening also changed the current `main` revision and visible application identity.

I therefore require a fresh explicit final evidence bundle against the exact candidate revision I intentionally want to accept. I do not backfill missing evidence from memory or infer a pass from older narrative records.

## Evidence that remains manual

I still need to perform and record manual acceptance for behavior that the automated browser gate cannot prove adequately:

- complete keyboard traversal and logical focus order;
- visible focus behavior across all interactive controls;
- screen-reader names, landmarks, reading order, status announcements, and mutation feedback;
- browser zoom and reflow at accessibility-relevant zoom levels;
- visual contrast, readability, spacing, hierarchy, and Glaze UI usability review;
- real browser permission grant, deny, disable, and externally revoked-permission behavior using the browser's actual permission UI;
- real operating-system notification presentation to confirm that the generic redacted content policy is preserved by supported browser/OS combinations;
- practical multi-tab behavior during ordinary use, including independent selection and no confusing alert duplication.

Automated Playwright and Axe success does not substitute for this manual acceptance.

## Evidence that remains target-environment specific

I still need target-environment validation before production migration can be considered:

- central Caddy proxy behavior for a long-lived SSE connection over the approved private HTTPS publication path;
- human-session revocation, password-reset invalidation, user deactivation, idle expiry, and absolute expiry against a real long-lived stream;
- prolonged real network interruption and recovery rather than only browser-emulated offline transitions;
- final Docker runtime, filesystem permissions, persistent SQLite placement, non-root runtime, read-only filesystem, capability restrictions, and no-direct-host-port evidence;
- target backup scheduling, repository placement, retention, monitoring, and a recorded restore exercise;
- target Uptime Kuma registration and independent out-of-band evidence that a complete Notify outage can still generate and deliver an alert;
- final private DNS, NetBird, Caddy, and monitoring evidence without changing the existing ntfy production route prematurely;
- controlled producer and consumer migration evidence with ntfy retained until rollback is no longer required.

## Coherent pre-cutover evidence gate

Individual acceptance gates are necessary but are not sufficient when their evidence describes different source revisions.

Before I authorize cutover, I require one aggregate pre-cutover manifest validated by `deploy/acceptance/validate_pre_cutover_acceptance.py`. The aggregate validator SHA-256 pins the issue #23 backup/restore evidence, issue #24 monitoring evidence, issue #25 all-scope target-preflight report, and issue #55 manual browser/OS evidence. It requires all four artifacts to describe the same exact HTTPS candidate and 40-character Git revision and invokes the real source validators for the subordinate gates.

The same aggregate record also requires parallel producer and consumer validation, authentication/authorization validation, an exercised rollback, and a recorded rollback procedure while ntfy is still active. ntfy must not already be retired, and cutover must remain unperformed for the pre-cutover manifest to pass.

A passing aggregate manifest proves evidence convergence and pre-cutover readiness. It does not promote Stable, set production acceptance to true, perform cutover, or retire ntfy. Final cutover and post-cutover verification remain a separate deliberate administrative operation.

## Stable-version gate

I will consider the current Notify web implementation ready to advance from acceptance/stabilization only when all applicable conditions below are satisfied:

1. The intended exact repository head is green across CI, browser/accessibility, production-readiness, and monitoring-readiness gates.
2. No unexplained browser, backend, production-readiness, or monitoring failure remains open.
3. Manual keyboard, screen-reader, reflow, visual, and browser-notification acceptance is recorded and the source-controlled issue #55 evidence validator passes against the exact accepted candidate revision.
4. Target Caddy/SSE and long-lived-session behavior is validated.
5. Backup and restore evidence is current and demonstrates recovery rather than backup creation alone.
6. Monitoring includes independent evidence for detecting a complete Notify outage.
7. Security and privacy boundaries remain fail-closed and no reusable secret is introduced into source, test fixtures, logs, or documentation.
8. Issues #23, #24, #25, and #55 converge in one passing coherent pre-cutover manifest for the same candidate revision.
9. Parallel producer/consumer migration and authorization behavior are validated and rollback is exercised while ntfy remains active.
10. Project metadata, README guidance, change records, and relevant infrastructure records accurately describe the state that was actually validated.
11. Source release metadata is intentionally advanced only after the required target/manual acceptance evidence and controlled cutover/post-cutover validation exist; production-mode configuration or aggregate pre-cutover PASS alone is never treated as final production acceptance.

## Current conclusion

The repository has strong source-controlled evidence for the Milestone 4 web implementation, but I do not yet classify GoreeCloud Notify as a stable production version. The remaining work is real acceptance evidence, target-environment validation, coherent same-candidate convergence, and controlled migration—not additional Milestone 4 feature expansion.
