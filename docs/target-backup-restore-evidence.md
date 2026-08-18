# GoreeCloud Notify Target Backup and Restore Evidence

## Purpose

I use this procedure to record and validate the real target-environment backup and restore evidence required by GitHub issue #23 before I approve GoreeCloud Notify for production or allow ntfy retirement.

The validator is read-only. It does not create a repository, choose my RPO, create a backup, restore production data, rotate credentials, configure monitoring, or approve production. It verifies that the evidence produced by those separately controlled operations is complete, internally consistent, revision-bound, sanitized, and aligned with the source recovery contract.

## Source authority

The machine-readable contract is:

`deploy/recovery/target_backup_restore_contract.json`

The validator is:

`deploy/recovery/validate_target_evidence.py`

The contract is bound to GitHub issue #23. While target recovery acceptance is pending, the candidate must continue to report:

- `release_stage: release_candidate`;
- `production_accepted: false`;
- `acceptance_status: pending`.

A successful backup or restore exercise does not promote the release by itself.

## Evidence file handling

I keep the real target evidence outside source control or under an ignored filename matching:

`goreecloud-notify-target-recovery-evidence*.json`

The record is Internal acceptance evidence. I sanitize it before permanent storage. I record references to protected credentials rather than reusable credential values, and I do not include passwords, tokens, private keys, cookies, session material, database URLs containing secrets, raw private notification content, or repository encryption secrets.

## Required target evidence

### Candidate identity

I record the exact HTTPS candidate address and exact 40-character Git revision being accepted. The snapshot and alternate restore must both identify the same source revision so recovery evidence from an older candidate cannot be silently reused for a newer one.

### Target data path

I record the authoritative SQLite path, owner, group, restrictive file mode, and proof that the intended application runtime can read and write the database. The validator rejects database modes that grant permissions to other users, omit owner read/write access, or make the database executable.

### Backup repository and recoverability

I record:

- repository type;
- a non-secret destination reference;
- encryption or equivalent provider protection;
- independence from the primary Notify runtime;
- independence from primary application storage;
- proof that repository credentials remain recoverable when the primary application host is unavailable;
- a non-secret credential-record reference;
- the approved administrative recovery path.

The evidence does not embed repository passwords, encryption keys, tokens, or other reusable secrets.

### RPO, frequency, and retention

I explicitly record the approved backup frequency, maximum RPO, recovery-point retention duration, minimum recovery-point count, and pre-change recovery-point requirement. The validator does not invent these values. It requires positive concrete values and rejects a backup interval that is longer than the recorded maximum RPO.

### Failed and missed backup monitoring

I record both failed-backup and missed-backup monitoring, the monitoring mechanism and alert path, and evidence that the alert path is in a separate failure domain. The final production backup failure path must not depend solely on GoreeCloud Notify or the same runtime host. I perform a controlled failed or missed backup test and record that an approved administrator actually received the alert.

### Real snapshot

The selected target snapshot must use the repository's SQLite Online Backup API path and record:

- capture time;
- exact candidate build revision;
- Alembic revision;
- exact SHA-256 digest;
- nonzero artifact size;
- successful SQLite integrity check;
- successful foreign-key check;
- sanitized manifest state.

The production backup repository may protect the resulting snapshot through Kopia or another approved recovery repository. The application snapshot itself remains transactionally consistent before repository protection.

### Alternate-location application restore

Routine validation is non-destructive. I restore to an alternate controlled location rather than overwriting production merely to prove recovery.

I record:

- alternate-location confirmation;
- confirmation that production was not overwritten;
- a non-secret restore-location reference;
- start and completion timestamps;
- observed recovery duration in seconds rather than an unsupported RTO estimate;
- source and restored-artifact SHA-256 values matching the verified backup;
- exact matching application build revision;
- post-restore Alembic revision and validation result;
- file ownership/permission validation;
- `/healthz` validation;
- approved test human authentication;
- expected application-state validation;
- producer authorization validation;
- inbox isolation validation;
- read/acknowledgement-state validation.

### Security-state reconciliation

A historical restore can revive historical security state. Before I treat the restore as acceptable, I record that I:

- revoked restored human web sessions;
- reviewed restored producer-token state against the current approved producer record;
- reviewed user active-state values;
- reviewed administrator authority;
- reviewed password-reset state;
- interpreted recovered login/security history as historical rather than current chronology;
- used current authoritative identity records during reconciliation.

The validator requires these reviews but does not automatically rotate producer credentials or make destructive identity changes. Those remain administrator decisions based on the age and circumstances of the restore point.

### Restore environment disposition

I record whether the alternate recovery environment was disposed of or deliberately retained under controlled status. I also record the rollback/disposition decision and confirm that the routine restore test left production data unchanged.

## Evidence shape

A sanitized evidence file follows this structure:

```json
{
  "schema_version": 1,
  "evidence_kind": "goreecloud-notify-target-backup-restore-acceptance",
  "sanitized": true,
  "captured_at": "2026-08-18T22:45:00-05:00",
  "candidate": {},
  "data_path": {},
  "backup_repository": {},
  "backup_policy": {},
  "backup_monitoring": {},
  "snapshot": {},
  "alternate_restore": {},
  "security_reconciliation": {},
  "disposition": {},
  "privacy": {
    "raw_notification_content_recorded": false,
    "reusable_secrets_recorded": false,
    "repository_secret_values_recorded": false,
    "evidence_sanitized": true
  }
}
```

The validator's exact-key rules intentionally reject undocumented fields so a secret-bearing or ambiguous field cannot be casually added to an accepted bundle.

## Validation

After I complete the real target exercise and sanitize the evidence, I run:

```bash
python deploy/recovery/validate_target_evidence.py \
  goreecloud-notify-target-recovery-evidence.json \
  --expected-revision <exact-deployed-git-sha>
```

The validator fails closed when, among other conditions:

- the candidate, snapshot, or restore revision does not match the explicitly expected revision;
- production acceptance is incorrectly reported as complete;
- the target database path, ownership, permissions, or runtime-access evidence is incomplete;
- the backup repository is not independent/protected/recoverable enough for the recorded contract;
- RPO, frequency, retention, or recovery-point values are missing or invalid;
- failed/missed backup monitoring depends on Notify or the same runtime host;
- the controlled backup-monitoring failure test or administrator receipt is missing;
- the snapshot method, digest, size, integrity, foreign-key, Alembic, or manifest evidence is invalid;
- the restore is not alternate-location and non-destructive;
- the restored artifact is not hash-bound to the selected verified backup;
- observed recovery time is absent;
- application, authentication, producer, inbox, read/ack, ownership, or health validation is incomplete;
- security-state reconciliation is incomplete;
- disposition is unrecorded;
- prohibited sensitive-data fields or privacy violations are present.

A PASS means the sanitized record satisfies the source issue #23 evidence contract. It does not make the underlying target observations true by itself; the real backup, monitoring, restore, and reconciliation operations remain the evidence source.

## Closure procedure for issue #23

I close issue #23 only after:

1. I have an approved target backup repository/destination and independently recoverable credential path.
2. I have recorded and approved concrete backup frequency, maximum RPO, retention, and recovery-point count.
3. Failed and missed backup monitoring is active through an independent path and a controlled failure/miss reaches an approved administrator.
4. I create and verify a real target SQLite Online Backup API recovery point from the exact candidate revision.
5. I perform a non-destructive alternate-location application restore from that recovery point.
6. I record the observed recovery time and complete application-level validation.
7. I complete the required restored-security-state reconciliation.
8. I sanitize the evidence and the validator passes with `--expected-revision` set to the exact intended candidate revision.
9. I update issue #23 and the permanent GoreeCloud records with the actual result.

Issue #23 closure remains necessary but not sufficient for production acceptance. Issue #24 monitoring/out-of-band evidence, issue #25 target runtime/private publication, issue #55 manual browser/OS acceptance, controlled producer/consumer migration, and tested ntfy rollback remain separate gates.
