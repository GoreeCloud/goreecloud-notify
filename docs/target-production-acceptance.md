# GoreeCloud Notify target production acceptance

## Purpose

I use this runbook to collect target-environment production-readiness evidence for GoreeCloud Notify after the source-controlled readiness gates are green and before I approve a production cutover from ntfy.

This runbook does **not** approve deployment, change `notify.goreecloud.com`, retire ntfy, modify Caddy, DNS, AdGuard Home, NetBird, Uptime Kuma, backup schedules, producer credentials, or application data. It separates read-only evidence collection from later controlled change work.

The source-controlled production contract remains defined by `docker-compose.production.yml`, `deploy/production/runtime.env.example`, `deploy/caddy/notify.goreecloud.com.caddy`, `docs/production-runtime.md`, `docs/backup-recovery.md`, and `docs/monitoring-alert-readiness.md`.

## Safety boundary

I will not run the target preflight against the current live `notify.goreecloud.com` route while that hostname still serves ntfy and interpret the result as GoreeCloud Notify evidence.

I will use the preflight only when one of these conditions is true:

- GoreeCloud Notify is running on an approved isolated candidate/staging route that represents the final target topology; or
- I am inside an explicitly approved controlled cutover window in which the hostname is intentionally routed to the candidate Notify runtime and the ntfy rollback path is preserved.

The preflight is read-only. It does not create directories, change ownership or permissions, restart containers, run migrations, modify Caddy, change DNS, change NetBird policy, create monitoring objects, create backup jobs, rotate credentials, or alter application state.

## Evidence collector

`deploy/target/preflight.py` is the source-controlled read-only target checker.

It supports separate `host`, `network`, and `all` scopes so I do not have to pretend the production host and an approved private-network client have the same visibility. It accepts only non-secret arguments appropriate to the selected scope:

- target HTTPS origin for network validation;
- exact 40-character source revision expected in the deployed image;
- container name for host validation;
- approved persistent data directory path for host validation;
- protected runtime environment-file path for host validation;
- bounded runtime-log line count;
- local evidence-output path.

The checker does **not** read or print the runtime environment file. It records only its owner/group and mode. It does not use `docker inspect` to dump environment variables. The runtime log scan reports only marker names/counts and never prints matched log content.

The JSON evidence contains internal infrastructure details such as target paths, image identity, and private DNS addresses. I will therefore treat the generated report as an Internal GoreeCloud record, review it before sharing or committing it, and keep it outside normal source control by default.

## Prerequisites

Before I run target preflight I will identify and record:

- target host and administrative account;
- exact candidate Git revision;
- exact candidate image/tag intended for validation;
- running GoreeCloud Notify container name;
- approved persistent data directory;
- protected runtime environment-file path;
- candidate HTTPS origin;
- whether the route is isolated/staging or part of an explicitly approved cutover window;
- retained ntfy rollback route/runtime state.

I will not copy active secret values into this runbook, issue comments, pull requests, terminal transcripts, evidence JSON, or change logs.

## Run the source self-test

Before relying on the checker on a target host:

```bash
python3 deploy/target/preflight.py --self-test
```

Expected result:

```text
target preflight self-test passed
```

CI also executes this self-test so syntax and core evidence assertions remain regression-tested.

## Run target preflight

I split target-host evidence from approved-client network evidence unless one system is intentionally configured to provide both views. This avoids treating the server's own resolver or network position as proof of the end-user private access path.

### Host scope

From the checked-out exact candidate revision on the target Docker host:

```bash
python3 deploy/target/preflight.py \
  --scope host \
  --expected-revision <exact-40-character-git-sha> \
  --container goreecloud-notify \
  --data-dir <approved-persistent-data-directory> \
  --env-file <protected-runtime-environment-file> \
  --output goreecloud-notify-target-host-preflight.json
```

This scope checks Docker runtime identity, host filesystem permissions, image revision, and a bounded runtime-log tail. It does not make a DNS or HTTPS claim.

### Approved-client network scope

From an approved NetBird client that is intentionally using the GoreeCloud private DNS path:

```bash
python3 deploy/target/preflight.py \
  --scope network \
  --base-url https://<approved-notify-candidate-hostname> \
  --expected-revision <exact-40-character-git-sha> \
  --output goreecloud-notify-target-network-preflight.json
```

This scope checks private NetBird-space DNS resolution and the verified-TLS application contract through the candidate HTTPS route. It does not inspect Docker or target-host files.

### Combined scope

I may use `--scope all` only when the same system is intentionally suitable for both host and approved-client network evidence. I will not configure or weaken DNS merely to make the combined mode pass.

I will not replace placeholders with guessed paths, networks, revisions, or credentials.

A zero exit status means every assertion in the selected scope passed. A non-zero exit status leaves the JSON evidence in place with failed checks so the cause can be reviewed without changing the target system.

## Automated preflight scope

The checker validates the following read-only target state.

### Exact runtime identity

These checks belong to `--scope host` (or explicitly justified `--scope all`).

- the running container uses UID/GID `10001:10001`;
- the root filesystem is read-only;
- the PID limit is 256;
- `no-new-privileges` is enabled;
- all Linux capabilities are dropped;
- no host ports are published;
- only the approved `proxy` Docker network is attached;
- `/tmp` uses a tmpfs with `noexec` and `nosuid`;
- Docker reports the application healthy;
- `/data` is the expected bind mount;
- the running image ID/reference is recorded;
- the OCI `org.opencontainers.image.revision` label equals the exact expected Git revision.

### Filesystem and protected configuration

- the protected runtime environment file exists and has mode `0600` or narrowly controlled `0640`;
- its owner/group are recorded without reading its contents;
- the persistent application data directory is owned by `10001:10001`, is owner-writable/searchable, and grants no permissions to other users;
- `goreecloud_notify.db` is owned by `10001:10001`, is owner-writable, and grants no permissions to other users.

These checks do not prove that every configuration value inside the protected environment file is correct. Production startup and HTTPS application behavior provide separate fail-closed evidence for the settings the application validates.

### Private DNS and HTTPS application boundary

These checks belong to `--scope network` (or explicitly justified `--scope all`) and are run from an approved private-network client.

- the candidate hostname resolves only to IPv4 addresses inside NetBird `100.64.0.0/10` from the approved test client;
- TLS certificate verification succeeds through the normal system trust store;
- `/healthz` reports healthy state without exposing the build revision;
- `/api/v1/meta` reports production mode and the exact expected build revision;
- unauthenticated `/api/v1/me` is denied;
- unauthenticated `/api/v1/inbox/stream` is denied;
- the HTML shell remains non-cacheable;
- built frontend assets retain one-year immutable caching;
- same-origin credentialed CORS is preserved;
- the response privacy, CSP, anti-framing, `nosniff`, referrer, and Permissions-Policy contract is present through the target HTTPS route.

### Bounded runtime-log review

The checker reviews only the requested tail of the target container log and fails if it detects markers for:

- Authorization headers;
- bearer tokens;
- cookie headers;
- administrator-token assignments;
- password assignments.

This is a regression aid, not proof that every possible secret or sensitive value is absent. I will still perform a deliberate target log review before production approval.

## Evidence the automated preflight does not prove

A passing preflight is necessary evidence but does not close the production-readiness gate. I must still perform and record the following separately.

### Caddy and NetBird source authorization

- validate the complete active Caddy configuration before/after any approved route change;
- record the trusted certificate and final hostname;
- confirm an approved NetBird client can reach the final HTTPS route;
- confirm a deliberately unapproved source is denied;
- confirm the application still requires authentication after network authorization;
- record the exact source path used by Uptime Kuma so monitoring is not accidentally denied or overly broad.

### Authenticated long-lived SSE

Using an approved test account and the final HTTPS route, I will verify:

- an authenticated `text/event-stream` connection remains open for a representative long-lived period;
- Caddy does not introduce unintended buffering or premature termination;
- keepalive behavior is observable without leaking protected message content;
- reconnect resumes from the last processed Delivery cursor;
- session revocation terminates or invalidates the stream;
- password-reset invalidation terminates or invalidates the stream;
- user deactivation terminates or invalidates the stream;
- idle expiry terminates or invalidates the stream;
- absolute expiry terminates or invalidates the stream;
- a prolonged real network interruption recovers without lost or duplicate authoritative Delivery state.

I will record observed behavior and times rather than assuming disposable CI timing represents the real target.

### Backup and restore — issue #23

I will not close recovery readiness until I have target evidence for:

- approved backup destination/repository;
- independently recoverable backup/encryption credentials;
- backup frequency/RPO;
- backup-point retention;
- failed or missed backup monitoring through an independent path;
- actual target application-data ownership/permissions;
- at least one alternate-location application restore exercise;
- restored schema/application/authentication/notification/Delivery state validation;
- post-restore security-state reconciliation;
- observed recovery time from the completed exercise.

### Monitoring and out-of-band alerting — issue #24

I will not close monitoring readiness until I have target evidence for:

- actual Uptime Kuma monitor registration against the final private HTTPS `/healthz` route;
- final interval, retries, retry interval, timeout, accepted status, TLS behavior, notification assignment, and source path;
- healthy state without false alerting;
- controlled final-route DOWN detection;
- controlled RECOVERED detection in correct order;
- approved administrator receipt;
- monitor rollback/removal procedure;
- at least one tested Notify-down alert path that remains usable while GoreeCloud Notify itself is unavailable.

### Producer/consumer migration and rollback

Before ntfy retirement I will record:

- each producer migrated to the approved GoreeCloud Notify compatibility/native endpoint;
- least-privilege producer identity/token scope;
- controlled test delivery from each producer class;
- intended user/subscription behavior after migration;
- the exact ntfy route/runtime configuration retained for rollback;
- a tested rollback procedure that restores the prior ntfy service path if the Notify cutover fails;
- an explicit later approval before ntfy is retired.

## Target evidence record

For each target acceptance session I will record, without reusable secrets:

- Date and time in Central Time:
- Target host:
- Administrative account:
- Candidate hostname:
- Candidate Git revision:
- Candidate image reference/ID:
- Preflight JSON filename/location:
- Preflight result:
- Data directory owner/group/mode:
- Database owner/group/mode:
- Runtime environment-file owner/group/mode:
- Docker networks and host-port result:
- Private DNS result:
- Caddy validation result:
- TLS/certificate result:
- Approved NetBird source result:
- Denied source result:
- Authenticated web/session result:
- Long-lived SSE result:
- Session invalidation/expiry result:
- Real network interruption/recovery result:
- Backup/restore evidence reference:
- Uptime Kuma evidence reference:
- Independent outage-alert evidence reference:
- Producer migration evidence reference:
- ntfy rollback evidence reference:
- Runtime/log review result:
- Manual browser/accessibility evidence reference:
- Final disposition: blocked / continue validation / eligible for explicit cutover approval
- Follow-up actions:

## Failure handling

If any preflight or manual target check fails, I will stop treating the candidate as production-ready, preserve the relevant evidence, and return the failure to repair/stabilization. I will not weaken filesystem permissions, proxy trust, Caddy authorization, authentication, or monitoring merely to make a gate pass.

A failed target check is evidence that the candidate or deployment contract needs correction; it is not permission to bypass the gate.

## Completion boundary

Target production acceptance is complete only when the applicable evidence above is recorded together with the manual browser/accessibility gate and the license/release gate, no unexplained blocker remains, and the ntfy rollback path is still validated.

Completion of this runbook makes the candidate **eligible for a separate explicit production cutover decision**. It does not itself authorize deployment, hostname repointing, producer migration, or ntfy retirement.
