# ntfy Migration and Retirement Boundary

GoreeCloud Notify is the first-party replacement for ntfy. The replacement is executed as a controlled migration, not as a rename or an early deletion of the fallback service.

## Current production boundary

ntfy remains the active production notification service and tested rollback path until the final cutover gate passes. The current verified runtime inventory records container `ntfy` using `binwiederhier/ntfy:v2.26.3`, healthy on internal container port 80, with `https://notify.goreecloud.com` serving the established producer topics.

The current migration inventory contains these topics:

- `goreecloud-beszel`
- `goreecloud-diun`
- `goreecloud-healthchecks`
- `goreecloud-uptime`
- `goreecloud-validation`
- `netbird-alerts`

The ntfy-compatible publish path allows existing producers to move without a flag-day rewrite while native producer APIs remain the preferred end state.

## Native client gate

The repository now contains a first-party Flutter client shared by Linux and Android. CI produces:

- an amd64 Debian `.deb` package for Linux;
- an installable Android acceptance APK.

The native client uses the GoreeCloud Notify human-session API, stores only the opaque session cookie and CSRF token through platform secure storage, reads the authenticated inbox, consumes the realtime SSE stream, and exposes read/unread and acknowledgement actions. Local operating-system notification previews are deliberately redacted.

The initial Android acceptance artifact does **not** by itself authorize ntfy retirement. Persistent Android delivery after process termination must be demonstrated independently. Until that behavior is implemented and real-device accepted, ntfy remains the independent mobile alert fallback.

## Pre-cutover acceptance convergence

Before production cutover, issues #23, #24, #25, and #55 must each contain real evidence for the same exact GoreeCloud Notify candidate revision. The repository composes those gates through `deploy/acceptance/validate_pre_cutover_acceptance.py`.

The aggregate manifest must SHA-256 pin the real subordinate evidence files and prove that backup/restore, monitoring/out-of-band alerting, target runtime/private publication, and manual browser/OS acceptance all describe the same HTTPS candidate and Git revision.

The aggregate pre-cutover record also requires that ntfy is still active, representative producer and consumer validation passed during parallel operation, authentication and authorization validation passed, rollback was actually exercised and recorded, and cutover has not yet been performed.

A passing aggregate manifest establishes pre-cutover readiness only. It does not set production acceptance to true, promote Stable, retire ntfy, or perform migration.

## Controlled producer migration

Migrate producers one at a time while the ntfy fallback remains intact. For each producer:

1. identify its current topic and notification trigger;
2. send an equivalent synthetic notification through the Notify candidate;
3. verify persistence, fanout, authenticated inbox visibility, severity/title/body mapping, and expected user-visible alert behavior;
4. change only that producer to the approved Notify endpoint or native producer API;
5. trigger a real representative event;
6. validate success through the application and independent monitoring path;
7. record the result before proceeding to the next producer;
8. roll that producer back immediately if any required behavior fails.

The initial producer order is Beszel, DIUN, Healthchecks, Uptime Kuma, validation automation, then NetBird alerts. This order is operational guidance rather than permission to skip producer-specific validation.

## Final hostname cutover

The final `notify.goreecloud.com` authority moves only after the coherent pre-cutover bundle and native-client gate are accepted. The cutover operation must:

1. identify the exact candidate revision that passed acceptance;
2. capture a fresh recovery point for both Notify and the current ntfy state;
3. confirm independent outage alerting remains available outside the component being changed;
4. update the approved Caddy/private-publication route so `notify.goreecloud.com` targets GoreeCloud Notify;
5. validate HTTPS, health, login, inbox, realtime delivery, all six compatibility topics, and native producer requests through the final hostname;
6. validate the Linux `.deb` client and Android APK against the final hostname;
7. keep ntfy stopped-but-recoverable through the rollback observation window rather than deleting it immediately;
8. roll back the route and producer changes if any required condition fails.

## ntfy retirement from the VPS

Permanent deletion is allowed only after the final hostname and producer/consumer paths have remained accepted through the defined observation window. The operator must inspect the live host before destructive changes and record the exact stack/configuration paths actually present.

Retirement removes, in this order:

1. the ntfy container and Compose service;
2. ntfy-only configuration and persistent application data after a verified final archive/recovery point exists;
3. the `binwiederhier/ntfy:v2.26.3` image if no other container uses it;
4. ntfy-only Caddy/backend references;
5. ntfy-specific monitoring, backup-source, health-check, and automation dependencies;
6. obsolete package, network, volume, and environment-file artifacts that are proven to belong only to ntfy.

The operation must not delete shared Docker networks, shared Caddy state, unrelated monitoring integrations, or common secret/configuration directories merely because ntfy used them.

## Documentation retirement

Current-state documentation must track reality. Therefore ntfy references are removed from active inventories, current architecture descriptions, future plans, and operational procedures only after runtime retirement is verified. The dedicated `Inventory — ntfy Subscribed Topics` record is then deleted or explicitly retired according to documentation governance.

Historical change-log entries are retained. They record the fact that ntfy previously existed and the migration work that replaced it; deleting those historical entries would damage the authoritative history rather than complete the migration.

## Rollback principle

Rollback is a demonstrated capability, not a document-only promise. Removal of ntfy is never evidence that migration succeeded. Migration succeeds only when Notify has passed the required acceptance evidence, the controlled cutover behaves as intended, the native clients meet their required delivery behavior, the rollback path has been proven, and the approved observation window completes without a blocking failure.
