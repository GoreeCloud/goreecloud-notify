# ntfy Migration Boundary

GoreeCloud Notify is being built alongside ntfy, not in place of it yet.

## Current production boundary

ntfy remains the active production notification service and the tested rollback path. Source validation, a production-mode Notify runtime, or completion of one individual acceptance issue does not authorize ntfy retirement.

The current migration inventory contains these ntfy topics:

- `goreecloud-beszel`
- `goreecloud-diun`
- `goreecloud-healthchecks`
- `goreecloud-uptime`
- `goreecloud-validation`
- `netbird-alerts`

The initial milestones changed none of them. The compatibility publishing path allows producers to move gradually rather than requiring a flag-day migration.

## Pre-cutover acceptance convergence

Before I authorize production cutover, issues #23, #24, #25, and #55 must each have real evidence for the same exact GoreeCloud Notify candidate revision.

The repository composes those individual gates through:

`deploy/acceptance/validate_pre_cutover_acceptance.py`

The aggregate manifest must SHA-256 pin the real subordinate evidence files and prove that backup/restore, monitoring/out-of-band alerting, target runtime/private publication, and manual browser/OS acceptance all describe the same HTTPS candidate and Git revision.

The aggregate pre-cutover record also requires:

- ntfy is still active;
- ntfy has not been retired;
- representative producer validation passed during parallel operation;
- representative consumer validation passed;
- authentication and authorization validation passed;
- rollback was actually exercised;
- the rollback procedure is recorded;
- cutover has not yet been performed.

A passing aggregate manifest establishes pre-cutover readiness only. It does not set production acceptance to true, promote Stable, retire ntfy, or perform migration.

## Controlled cutover

Final cutover remains a separate deliberate administrative operation after the coherent pre-cutover gate passes.

Before changing producer or consumer authority, I must:

1. identify the exact candidate revision that passed the coherent pre-cutover gate;
2. confirm the most recent recovery point and rollback path remain usable;
3. confirm independent outage alerting remains available during the change;
4. preserve ntfy until the intended producer and consumer paths are verified on Notify;
5. migrate in controlled increments rather than removing the fallback first;
6. validate authentication, authorization, delivery, and user-visible behavior after each material migration step;
7. roll back immediately when a migration condition fails rather than forcing completion;
8. record the final cutover and post-cutover validation separately from the pre-cutover acceptance bundle.

Only after successful controlled cutover and post-cutover validation may I consider retiring ntfy and intentionally changing GoreeCloud Notify release/production-acceptance metadata.

## Rollback principle

Rollback is a demonstrated capability, not a document-only promise. The pre-cutover aggregate gate requires a real rollback exercise while ntfy remains available so the fallback is proven before it is needed.

I do not treat removal of ntfy as evidence that migration succeeded. The migration succeeds only when Notify has passed the required acceptance evidence, the controlled cutover behaves as intended, and the rollback path is no longer needed according to the approved change record.
