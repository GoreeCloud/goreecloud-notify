# GoreeCloud Notify Coherent Pre-Cutover Acceptance Evidence

## Purpose

I use this procedure to prove that the major GoreeCloud Notify acceptance gates describe one coherent release candidate before I authorize a production cutover away from ntfy.

The aggregate validator does not perform backup/restore testing, provision monitoring, run the target preflight, perform manual browser/OS acceptance, migrate producers or consumers, retire ntfy, promote a Stable release, or set production acceptance to true. Each underlying gate remains independently responsible for its own real evidence.

The aggregate layer exists to prevent evidence skew. I do not want to accept backup evidence from one revision, monitoring evidence from another revision, manual browser evidence from a third revision, and target-publication evidence from a fourth revision as though they described one product.

## Source authority

The machine-readable contract is:

`deploy/acceptance/pre_cutover_acceptance_contract.json`

The validator is:

`deploy/acceptance/validate_pre_cutover_acceptance.py`

The aggregate record remains a **pre-cutover** contract. A passing record must still report:

- release stage `release_candidate`;
- `production_accepted: false`;
- acceptance status `pending`;
- ntfy active;
- ntfy not retired;
- cutover not performed.

A PASS means one coherent evidence set exists for one exact candidate. It does not authorize the validator itself to change any of those states.

## Required subordinate evidence

I place the sanitized aggregate manifest and its four referenced evidence files in one controlled evidence directory. Each referenced file is relative to that directory and is SHA-256 pinned by the manifest.

### Issue #23 — backup and restore

The aggregate validator invokes:

`deploy/recovery/validate_target_evidence.py`

The evidence must already satisfy the issue #23 target recovery contract, including exact candidate revision binding, target data-path evidence, independent repository/recoverability, RPO and retention, independent failed/missed-backup monitoring, verified SQLite snapshot identity, alternate-location restore, observed recovery time, and restored-security-state reconciliation.

### Issue #24 — monitoring and out-of-band alerting

The aggregate validator invokes:

`deploy/monitoring/validate_target_evidence.py`

The evidence must use monitoring schema v2 and already satisfy the issue #24 contract, including the exact candidate URL and Git revision, live Uptime Kuma/Caddy evidence, DOWN/RECOVERED administrator receipt, preserved ntfy monitoring, rollback documentation, and an independent Notify-down alert path.

### Issue #25 — target runtime and private publication

The aggregate validator reads the actual `goreecloud-notify-target-preflight-v2` report produced by the source target preflight.

The report must:

- use scope `all`;
- have overall result `pass`;
- identify the same exact HTTPS candidate URL;
- identify the same exact expected Git revision;
- contain completed checks whose statuses are all `pass`.

A partial network-only or host-only preflight cannot satisfy the aggregate gate.

### Issue #55 — manual browser and operating-system acceptance

The aggregate validator invokes:

`deploy/acceptance/validate_manual_browser_evidence.py`

The evidence must already satisfy the issue #55 contract for the same candidate URL and revision, including the required real keyboard, screen-reader, reflow, Glaze UI, appearance, filter, realtime, permission, OS-alert, and reconnect/replay observations.

## Evidence identity and tamper resistance

The aggregate manifest records, for each subordinate evidence file:

- a relative file path;
- a lowercase SHA-256 digest.

The validator recomputes every digest before using the evidence. It rejects:

- a missing referenced file;
- a path outside the manifest evidence directory;
- an absolute path;
- `..` traversal;
- a digest mismatch;
- two acceptance gates pointing to the same evidence artifact;
- a subordinate candidate URL or revision that differs from the aggregate candidate.

The subordinate evidence is then passed through its actual source validator where one exists. The aggregate layer therefore composes the individual gate contracts rather than reimplementing or weakening them.

## Migration and rollback evidence

The aggregate record also requires controlled pre-cutover migration evidence. Before the aggregate can pass, I record that:

- ntfy remains active;
- ntfy has not been retired;
- representative producer validation passed while parallel operation was available;
- representative consumer validation passed;
- authentication and authorization behavior was validated;
- rollback was actually exercised rather than merely described;
- the rollback procedure is recorded;
- production cutover has not yet been performed.

I also include a sanitized evidence summary describing what was tested. The summary is not a substitute for the detailed operational records and must not contain reusable secrets or raw private notification content.

The pre-cutover gate deliberately requires a rollback exercise while ntfy is still available. I do not remove the fallback first and then try to prove that it would have worked.

## Privacy boundary

The aggregate manifest is sanitized metadata and references. It must not embed the subordinate evidence files or raw sensitive artifacts.

The manifest must record:

- `sanitized: true`;
- no raw notification content recorded;
- no reusable secrets recorded;
- subordinate evidence files are referenced rather than embedded.

The validator also rejects unexpected secret-bearing field names such as token values, passwords, authorization material, private keys, and recovery codes. Protected operational evidence remains in its approved controlled location.

## Manifest structure

A final sanitized manifest follows this shape:

```json
{
  "schema_version": 1,
  "manifest_kind": "goreecloud-notify-pre-cutover-acceptance",
  "sanitized": true,
  "captured_at": "2026-08-18T23:00:00-05:00",
  "candidate": {
    "service_url": "https://notify.goreecloud.com",
    "build_revision": "<exact-40-character-git-sha>",
    "release_stage": "release_candidate",
    "production_accepted": false,
    "acceptance_status": "pending"
  },
  "evidence_files": {
    "backup_restore": {"path": "backup-restore.json", "sha256": "<sha256>"},
    "monitoring": {"path": "monitoring.json", "sha256": "<sha256>"},
    "target_preflight": {"path": "target-preflight.json", "sha256": "<sha256>"},
    "manual_browser_os": {"path": "manual-browser-os.json", "sha256": "<sha256>"}
  },
  "migration_rollback": {},
  "privacy": {
    "sanitized": true,
    "raw_notification_content_recorded": false,
    "reusable_secrets_recorded": false,
    "embedded_evidence_files": false
  }
}
```

## Validation

I run:

```bash
python deploy/acceptance/validate_pre_cutover_acceptance.py \
  /protected/evidence/notify/pre-cutover-acceptance.json \
  --expected-revision <exact-candidate-git-sha>
```

The validator fails closed if the manifest candidate does not match the explicit revision, if any subordinate artifact digest is wrong, if any subordinate gate fails its own source validator, if issue #25 does not contain an all-scope passing target preflight for the same URL and revision, if migration/rollback requirements are incomplete, if ntfy is already retired, if cutover is already recorded as performed, or if the privacy boundary is violated.

## Pre-cutover acceptance boundary

A PASS establishes only this conclusion:

> I have one sanitized, internally coherent pre-cutover acceptance set in which issues #23, #24, #25, and #55 all describe the same exact GoreeCloud Notify candidate, and I have validated parallel migration and rollback while ntfy remains active.

It does **not** establish:

- that GoreeCloud Notify is already Stable;
- that production acceptance is already true;
- that ntfy may be removed automatically;
- that producer or consumer cutover has already occurred;
- that a post-cutover verification has completed.

After a real aggregate PASS, final cutover remains a separate deliberate administrative operation with its own change record, current recovery point, rollback decision, and post-cutover verification. Only after that controlled operation succeeds should I consider changing release/acceptance metadata and retiring ntfy according to the approved migration procedure.
