# GoreeCloud Notify Backup and Restore Recovery

## Status

This document defines the source-controlled GoreeCloud Notify SQLite backup and recovery procedure used for development and recovery-readiness validation.

It does **not** create a production backup repository, schedule, retention policy, RPO, monitoring assignment, production secret, or production deployment. Those target-environment decisions remain separate production gates.

## Recovery objective

GoreeCloud Notify must be recoverable as an application, not merely as a database file.

A usable recovery point must preserve the application data needed to reconstruct the expected Notify state, including users, administrator authority, service identities, sources, channels, producer-token records, subscriptions, notifications, Deliveries, preferences, audit state, and Alembic schema revision. The matching application release and non-secret deployment configuration must remain available separately.

Reusable credentials and protected production configuration are not copied into repository documentation or backup manifests.

## SQLite snapshot method

The repository provides `python -m app.backup` for SQLite snapshot creation and verification.

The `create` command uses Python's SQLite Online Backup API through `sqlite3.Connection.backup()`. This creates a transactionally consistent SQLite snapshot without defining production backup as an unconditional filesystem copy of a live database.

Example from the `backend/` directory:

```bash
python -m app.backup create \
  --destination /approved/recovery/location/goreecloud_notify-YYYYMMDD-HHMMSS.db
```

The configured `GOREECLOUD_NOTIFY_DATABASE_URL` is used unless `--database-url` is supplied explicitly.

The command:

- requires a file-backed SQLite source database;
- refuses to overwrite an existing backup file;
- writes through a temporary partial file and atomically renames the completed snapshot;
- runs `PRAGMA integrity_check`;
- runs `PRAGMA foreign_key_check`;
- verifies the current GoreeCloud Notify SQLAlchemy tables are present;
- verifies the `alembic_version` record exists;
- calculates a SHA-256 digest;
- records file size, Alembic revision, table count, creation time, and backup-format identifier in a separate JSON manifest;
- does not place the database URL, passwords, tokens, cookies, CSRF values, or other reusable credentials in the manifest.

## Snapshot verification

Verify a recovery snapshot before relying on it:

```bash
python -m app.backup verify \
  --backup /approved/recovery/location/goreecloud_notify-YYYYMMDD-HHMMSS.db
```

Verification is read-only and fails when integrity, foreign-key consistency, required tables, or Alembic revision evidence is missing.

The verification path is intentionally isolated from the configured application runtime database. Loading model metadata for `verify` no longer initializes the normal SQLAlchemy engine, creates the configured runtime database parent directory, or requires the configured production database path to be writable or even available. This allows an extracted recovery artifact to be verified in a restricted recovery container or alternate host without introducing an unrelated placeholder application database merely to import the verifier.

Only `create` needs a live database URL. Its configuration lookup remains lazy so `verify` and `revoke-restored-sessions` operate solely on their explicitly supplied recovery artifact paths.

A successful verification is necessary but is not by itself sufficient recovery evidence. Application-level restore validation is also required.

## Backup scope outside the SQLite file

The SQLite snapshot is only one recovery component.

The recovery record must also identify, without embedding reusable secrets:

- the exact GoreeCloud Notify release, commit, or immutable image used by the recovery point;
- the Alembic revision contained in the snapshot;
- non-secret Docker/Compose and application configuration required to reconstruct the runtime;
- references to the protected secret/configuration source used by the target environment;
- the Caddy/private-publication configuration required by the final deployment;
- the approved backup-repository location and the independent credentials required to reach it;
- the administrative network path used during recovery.

Caddy, AdGuard Home, NetBird, monitoring, backup-repository credentials, and other external infrastructure are not assumed to be contained in the application database.

## Alternate-location restore validation

Routine restore testing must use an alternate controlled location. Do not overwrite a production database merely to prove that a backup can be read.

A recovery validation sequence is:

1. Select a verified snapshot and record its SHA-256 digest, manifest, application release/commit, and Alembic revision.
2. Copy the **already consistent backup artifact** to an alternate restore location. This is different from copying the live database while it may be changing.
3. Verify the copied restore database with `python -m app.backup verify`.
4. Invalidate restored human web sessions before allowing the recovered application to serve users:

   ```bash
   python -m app.backup revoke-restored-sessions \
     --database /alternate/restore/goreecloud_notify.db
   ```

5. Reconcile other security-sensitive state as described below.
6. Start the matching application release against the alternate database.
7. Run `alembic -c alembic.ini upgrade head` only under the selected recovery/upgrade procedure and matching release. A restored database may already be at head; the command must still be safe and explicit.
8. Verify `/healthz` and application startup.
9. Verify approved test human authentication after restored-session invalidation.
10. Verify expected sources, channels, subscriptions, notification history, Deliveries, service-identity/producer authorization behavior, and other expected data from the recovery point.
11. Verify inbox user isolation and expected read/acknowledgement state when those records are present in the recovery point.
12. Record the observed recovery result and dispose of the alternate test environment according to the approved validation procedure.

The automated backend regression suite performs this pattern with synthetic data: it creates an Alembic-managed database, exercises administrator/user/producer application behavior, creates an Online Backup API snapshot, restores it to an alternate path, revokes historical web sessions, re-runs Alembic to head, and verifies health, authentication, sources, channels, subscriptions, inbox Delivery state, and producer notification history against the restored database.

The suite also runs the standalone `verify` CLI while `GOREECLOUD_NOTIFY_DATABASE_URL` points at an intentionally non-creatable `/proc` location. That regression proves verification depends on the supplied backup artifact rather than normal runtime-engine initialization or a writable application data directory.

## Security-state reconciliation after restore

A historical database can restore historical security decisions. Recovery therefore requires an explicit reconciliation step.

### Human web sessions

All restored active `WebSession` records must be revoked before the recovered service is opened for normal use. The repository provides `revoke-restored-sessions` for this purpose, and the restore regression proves an old synthetic session cookie is rejected after reconciliation.

### Producer access tokens

The repository does **not** automatically rotate or disable every restored producer token. The administrator must compare restored token enablement/revocation state with the current approved producer inventory. For a materially stale disaster-recovery point, controlled token reconciliation or rotation should be preferred over silently trusting restored enabled state.

### User active state and administrator authority

Restored `User.is_active` and `User.is_admin` values must be checked against the current approved identity/administrator record when the restore point could predate a deactivation or authority change.

### Password-reset state

A restore point can predate a security-sensitive password reset. The administrator must determine whether the recovery point rewound a password change and, when necessary, perform another approved reset and session revocation before normal access resumes.

### Login-security state

Login-rate buckets and security-event history may also reflect the restore point rather than current chronology. They must be interpreted as recovered historical state, not as proof of events that occurred after the snapshot.

## Production backup design still required

This source-controlled implementation does not select the production backup schedule or storage target.

Before production approval, the target environment must still define and validate:

- backup frequency and RPO;
- backup recovery-point retention, separately from in-application notification retention;
- approved encrypted repository/destination;
- independently recoverable repository credentials;
- restrictive file ownership and permissions;
- monitoring for failed or missed backups;
- an alert path that does not depend solely on GoreeCloud Notify;
- pre-change recovery-point requirements before schema/application upgrades;
- at least one recorded target-environment application-level restore test;
- the observed recovery time from that test rather than an assumed RTO.

## Production and ntfy migration gate

GoreeCloud Notify must not replace ntfy solely because this repository-level recovery test passes.

Production deployment and ntfy retirement remain blocked until the target-environment backup/recovery configuration, independent monitoring/outage alerting, production runtime/private-publication controls, authentication/authorization hardening, and rollback evidence are all approved and validated.
