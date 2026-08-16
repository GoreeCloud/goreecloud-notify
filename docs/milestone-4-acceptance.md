# GoreeCloud Notify Milestone 4 Acceptance and Stabilization Record

## Purpose

I use this record to define the evidence I require before I treat the current GoreeCloud Notify Milestone 4 web implementation as stable enough for controlled target-environment validation or migration planning.

This record does not approve production deployment or ntfy replacement. GoreeCloud Notify remains draft, unmerged, and pre-production, and ntfy remains the current production notification service and rollback path.

## Stabilization state

I am treating the current source line as an acceptance and stabilization checkpoint rather than a feature-development checkpoint.

I will not classify the current web implementation as stable merely because automated tests pass. I require source-controlled validation, manual browser/accessibility acceptance, target-environment evidence, recovery evidence, monitoring evidence, and controlled migration evidence appropriate to the change being approved.

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

The ordinary CI gate separately verifies backend regression tests and locked frontend lint, TypeScript, and build checks. Production-readiness and monitoring-readiness workflows continue to verify the disposable source-controlled deployment and outage-alert contracts.

## Evidence that remains manual

I still need to perform and record manual acceptance for behavior that the automated browser gate cannot prove adequately:

- complete keyboard traversal and logical focus order;
- visible focus behavior across all interactive controls;
- screen-reader names, landmarks, reading order, status announcements, and mutation feedback;
- browser zoom and reflow at accessibility-relevant zoom levels;
- visual contrast, readability, spacing, and Glaze UI usability review;
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

## Stable-version gate

I will consider the current Notify web implementation ready to advance from acceptance/stabilization only when all applicable conditions below are satisfied:

1. The intended exact repository head is green across CI, browser/accessibility, production-readiness, and monitoring-readiness gates.
2. No unexplained browser, backend, production-readiness, or monitoring failure remains open.
3. Manual keyboard, screen-reader, reflow, visual, and browser-notification acceptance is recorded.
4. Target Caddy/SSE and long-lived-session behavior is validated.
5. Backup and restore evidence is current and demonstrates recovery rather than backup creation alone.
6. Monitoring includes independent evidence for detecting a complete Notify outage.
7. Security and privacy boundaries remain fail-closed and no reusable secret is introduced into source, test fixtures, logs, or documentation.
8. The migration plan preserves ntfy as a tested rollback path until controlled cutover is explicitly approved.
9. Project metadata, README guidance, change records, and relevant infrastructure records accurately describe the state that was actually validated.

## Current conclusion

The repository has strong source-controlled evidence for the Milestone 4 web implementation, but I do not yet classify GoreeCloud Notify as a stable production version. The remaining work is acceptance, target-environment validation, recovery and monitoring evidence, and controlled migration—not additional Milestone 4 feature expansion.