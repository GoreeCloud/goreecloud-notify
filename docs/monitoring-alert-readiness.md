# GoreeCloud Notify monitoring and outage-alert readiness

## Purpose

This document defines the current monitoring contract for GoreeCloud Notify after the permanent retirement of Uptime Kuma and ntfy from `goreecloud-vps-01` on September 18, 2026.

Repository tests may use synthetic monitoring and alert-sink components. Those fixtures are not production authority.

## Primary availability monitoring

The intended GoreeCloud-native primary availability monitor is **GoreeCloud Monitor**, after Monitor has independently completed its own production acceptance.

The required Notify health target is:

```text
GET https://notify.goreecloud.com/healthz
```

The monitor must observe the final approved private HTTPS route rather than only the application container/backend socket.

Target acceptance must record:

- exact Notify candidate revision;
- exact accepted GoreeCloud Monitor revision;
- monitor identity and active state;
- interval, retries, retry interval, and timeout;
- HTTP 200 policy and TLS verification;
- observed source at the approved HTTPS gateway;
- gateway authorization for that source;
- database-aware health behavior;
- healthy/no-false-alert observation;
- controlled DOWN then RECOVERED detection;
- approved administrator receipt.

The source contract is `deploy/monitoring/notify_monitoring_contract.json`. Sanitized target evidence is validated by `deploy/monitoring/validate_target_evidence.py`.

## Circular-dependency boundary

GoreeCloud Monitor may ordinarily publish service alerts through GoreeCloud Notify, but **Notify-down delivery cannot depend entirely on Notify itself**.

Before Notify production acceptance, at least one outage path must be demonstrated that:

- does not depend on GoreeCloud Notify;
- does not depend on the same runtime host;
- is in a separate material failure domain;
- is tested with a controlled Notify outage;
- reaches an approved administrator.

This independent path is required even after GoreeCloud Monitor is accepted.

## Disposable CI topology

The monitoring-readiness GitHub workflow still uses a disposable ntfy container as a synthetic write/read alert sink so the repository can test DOWN/RECOVERED sequencing, least-privilege publication/subscription boundaries, private HTTPS probing, and credential minimization.

That disposable fixture:

- is not production ntfy;
- is not a production dependency;
- does not establish an ntfy rollback path;
- does not establish a real independent failure domain;
- does not prove administrator receipt;
- does not replace target-environment evidence.

## Historical predecessor evidence

`deploy/monitoring/notify_uptime_kuma_monitor.json` is retained only as historical migration provenance. Uptime Kuma and ntfy are not active dependencies and are not ordinary production rollback targets.

## Rollback model

If a Notify activation fails:

1. preserve evidence;
2. restore the previous known-good GoreeCloud Notify application image/configuration;
3. restore compatible application data or the verified pre-change backup when required;
4. restore only directly affected private gateway/DNS/NetBird configuration;
5. disable/remove an unaccepted Notify monitor if necessary;
6. validate health, authentication, SSE, monitoring, and independent outage alerting again.

Do not silently restore ntfy or Uptime Kuma to production. Either requires separate explicit authorization.

## Production boundary

Source CI can validate contracts and synthetic behavior. Production monitoring readiness remains blocked until the exact target evidence proves:

- an accepted GoreeCloud Monitor deployment;
- final-route private HTTPS monitoring;
- real DOWN/RECOVERED behavior;
- approved administrator receipt;
- a tested independent Notify-down path in a separate failure domain;
- rollback/recovery evidence.

Only then may the monitoring gate be considered for production acceptance.
