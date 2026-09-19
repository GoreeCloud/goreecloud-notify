# GoreeCloud Notify target production acceptance

## Purpose

This runbook collects target-environment evidence for GoreeCloud Notify after ntfy retirement. It does not itself authorize deployment or production promotion.

The source-controlled production contract remains defined by the current production Compose/runtime files, target preflight, backup/recovery documentation, monitoring contract, current Glaze UI/platform records, and `/api/v1/meta` release-state contract.

## Safety boundary

Target preflight is read-only. It must be run only against the actual GoreeCloud Notify candidate being evaluated.

A passing preflight does not change `release_stage=release_candidate`, `production_accepted=false`, or `acceptance_status=pending`.

Do not treat historical ntfy/Uptime Kuma state as current acceptance evidence.

## Source self-test

Before using the target checker:

```bash
python3 deploy/target/preflight.py --self-test
```

Expected:

```text
target preflight self-test passed
```

## Host-scope preflight

From the exact reviewed checkout on `goreecloud-vps-01`:

```bash
python3 deploy/target/preflight.py \
  --scope host \
  --expected-revision <exact-40-character-git-sha> \
  --container goreecloud-notify \
  --data-dir <approved-persistent-data-directory> \
  --env-file <protected-runtime-environment-file> \
  --output goreecloud-notify-target-host-preflight.json
```

Host scope validates the hardened container identity, read-only filesystem, capability drop, no published ports, approved network attachment, tmpfs, health, exact image revision, protected file modes/ownership, persistent data ownership, and a bounded secret-marker log scan.

## Approved-client network preflight

From an approved private-network client using the intended private DNS path:

```bash
python3 deploy/target/preflight.py \
  --scope network \
  --base-url https://notify.goreecloud.com \
  --expected-revision <exact-40-character-git-sha> \
  --output goreecloud-notify-target-network-preflight.json
```

Network scope validates private DNS, verified TLS, `/healthz`, exact release metadata, security/correlation headers, unauthorized-path denial, cache policy, application identity resources, and same-origin credentialed CORS.

Use `--scope all` only when one system is intentionally suitable for both host and private-client evidence.

## Manual target gates not closed by preflight

### Private publication

Verify the currently approved HTTPS gateway and private-network policy:

- configuration validates successfully;
- trusted certificate is active;
- an approved private client can reach Notify;
- an unauthorized source is denied;
- application authentication remains required after network authorization.

### Authenticated SSE and session behavior

Verify through the final route:

- long-lived authenticated SSE remains open;
- no unintended buffering or premature termination occurs;
- reconnect resumes from authoritative delivery state;
- session revocation, password-reset invalidation, user deactivation, idle expiry, and absolute expiry invalidate access as designed;
- a representative real network interruption recovers without lost or duplicate authoritative delivery state.

### Backup and restore

Record:

- approved backup destination/repository;
- recoverable backup/encryption credentials;
- RPO/frequency and retention;
- missed/failed-backup alerting through an independent path;
- alternate-location restore;
- restored schema/application/authentication/notification/delivery state;
- post-restore security-state reconciliation;
- measured recovery time.

### Monitoring and independent outage alerting

Target evidence must satisfy `deploy/monitoring/validate_target_evidence.py` and prove:

- exact accepted GoreeCloud Monitor revision;
- final private HTTPS `/healthz` monitoring;
- concrete retry/timeout/TLS configuration;
- observed gateway source and authorization;
- healthy/no-false-alert behavior;
- controlled DOWN then RECOVERED detection;
- approved administrator receipt;
- a tested Notify-down path that does not depend on Notify or the same runtime host.

### Active producer migration

ntfy is retired, but historical producer configuration may still exist in other systems. Inventory actually active producers and migrate only those that still require notifications.

For each active producer record:

- producer identity;
- least-privilege GoreeCloud Notify credential scope;
- native or compatibility endpoint used;
- controlled test delivery;
- intended subscription/recipient behavior;
- removal of obsolete ntfy endpoint/token configuration.

Do not assume the historical producer inventory is still current.

### Glaze UI and platform acceptance

The current source implements a Glaze UI 1.5.1 source-adoption candidate, but production remains blocked until applicable browser/OS/native accessibility, performance, rollback, consumer-registry, and remaining nine-system platform requirements are accepted.

## Rollback/recovery model

Rollback is to the previous known-good GoreeCloud Notify release and compatible application data/configuration.

Before activation preserve:

- previous known-good image/revision;
- reviewed runtime/gateway/private-network configuration evidence;
- fresh application-data backup and restore evidence;
- current monitor configuration;
- acceptance timestamps/evidence.

Do not silently restore ntfy or Uptime Kuma to production. Either requires separate explicit authorization.

## Evidence record

For each acceptance session record, without reusable secrets:

- Central Time timestamp;
- target host;
- exact candidate revision/image;
- preflight report identifiers/results;
- protected file/data/database ownership/modes;
- Docker networks and no-host-port result;
- private DNS/TLS/gateway result;
- release/security/observability metadata result;
- authenticated session/SSE result;
- network interruption/recovery result;
- backup/restore evidence;
- GoreeCloud Monitor evidence;
- independent Notify-down evidence;
- active-producer migration evidence;
- rollback/recovery evidence;
- manual accessibility/Glaze evidence;
- platform-system evidence;
- final disposition and follow-up actions.

## Failure handling

Any failed required check returns the candidate to stabilization. Do not weaken filesystem permissions, private-network controls, authentication, security headers, observability requirements, monitoring, recovery, or platform requirements merely to make a gate pass.

## Completion boundary

Target acceptance is complete only when authoritative evidence shows the exact deployed candidate passed applicable runtime, private publication, recovery, monitoring, independent alerting, producer, Glaze/platform, and manual acceptance gates and explicit production approval exists.

A passing preflight is one artifact; it is not itself production approval.
