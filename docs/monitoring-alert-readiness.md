# GoreeCloud Notify monitoring and outage-alert readiness

## Purpose

I use this document to define the source-controlled monitoring contract and disposable outage/recovery evidence required before I register the future GoreeCloud Notify production monitor.

This work does not create a live Uptime Kuma monitor, change the current ntfy monitor, alter `notify.goreecloud.com`, install a Caddy rule, change AdGuard Home or NetBird, install a production notification credential, or prove an independent out-of-band outage path.

ntfy remains the current production notification service until the broader migration is intentionally approved.

## Monitoring role separation

GoreeCloud Notify delivers notifications. It does not replace the systems that determine whether a service is healthy.

I use Uptime Kuma as the primary GoreeCloud service-availability monitor. The future Notify availability monitor must therefore observe the final private HTTPS service path rather than only checking the application container directly.

The planned health target is:

```text
GET https://notify.goreecloud.com/healthz
```

The endpoint is database-aware: GoreeCloud Notify opens the configured SQLAlchemy engine and executes `SELECT 1` before returning the sanitized service health payload. A successful check therefore provides application/database reachability evidence rather than only static-process liveness.

## Proposed Uptime Kuma contract

`deploy/monitoring/notify_uptime_kuma_monitor.json` is the source-controlled proposed-not-provisioned monitor contract.

It defines:

- monitor name: `GoreeCloud Notify`;
- type: HTTP;
- method: GET;
- target: `https://notify.goreecloud.com/healthz`;
- interval: 60 seconds;
- accepted status: HTTP 200;
- TLS certificate and hostname verification required;
- private Caddy path required;
- database-aware health required.

The documented GoreeCloud Uptime Kuma source baseline is `172.19.0.50` on the shared proxy network. I do not treat that address as permanently authoritative for Notify merely because another GoreeCloud application used it successfully. Before production activation I must observe the actual source address reaching the real Caddy runtime and record the exact approved value.

The production Caddy proposal therefore uses the environment placeholder `GOREECLOUD_NOTIFY_MONITOR_SOURCE` instead of hard-coding the disposable source. The target-host Caddy environment must supply the verified source IP or CIDR before monitor activation.

## Existing ntfy monitor preservation

The current ntfy monitor is production state and must remain intact while GoreeCloud Notify is being validated.

The documented baseline to reverify before cutover is:

- monitor name: `ntfy`;
- type: HTTP;
- target: `http://ntfy:80/v1/health`;
- interval: 60 seconds;
- retries: 3;
- retry interval: 60 seconds;
- request timeout: 48 seconds;
- accepted response class: 200–299;
- existing notification assignment present.

These values are recorded in the Notify monitoring contract as a migration baseline, not as permission to edit the live monitor. Immediately before any cutover I will read the live Uptime Kuma monitor again and preserve its actual configuration and history before changing anything.

## Migration notification path

During parallel migration the disposable/source-level gate reproduces the existing GoreeCloud Uptime Kuma notification boundary:

```text
Uptime Kuma-like monitor
        |
        | write-only
        v
ntfy internal Docker endpoint
http://ntfy:80
        |
        v
goreecloud-uptime
        |
        | read-only
        v
validation subscriber
```

The planned service identity is `uptime-kuma` with write-only access to `goreecloud-uptime`.

The only source-controlled Notify availability transition titles are:

- `GoreeCloud Notify DOWN`
- `GoreeCloud Notify RECOVERED`

The approved minimized bodies identify only the service state and direct the administrator to Uptime Kuma and protected service logs. They do not include raw application responses, environment values, database URLs, passwords, tokens, session cookies, CSRF values, private keys, recovery codes, or authorization headers.

## Least-privilege alert-delivery contract

The disposable gate requires all four negative authorization checks:

1. the write-only monitor publisher cannot subscribe/read;
2. the read-only validation subscriber cannot publish;
3. an anonymous client cannot subscribe/read;
4. an anonymous client cannot publish.

A working alert path is not sufficient if the monitoring identity can read notification history or the validation subscriber can publish arbitrary alerts.

## Disposable readiness topology

The permanent GitHub Actions gate uses synthetic data and credentials only.

It builds the production GoreeCloud Notify image from the stacked runtime-readiness branch and creates an internal Docker-only topology containing:

- GoreeCloud Notify;
- Caddy with disposable internal TLS;
- ntfy v2.26.3 as the temporary migration alert destination;
- a fixed synthetic monitor source at `172.19.0.50`;
- a separate read-only validation subscriber.

No service publishes a host port.

The disposable Caddy fixture allows the NetBird range plus the fixed synthetic Uptime Kuma source and returns HTTP 403 outside that source boundary. The monitor performs normal TLS hostname validation using the disposable Caddy CA.

## State-transition validation

The gate proves the following sequence:

1. initialize the disposable SQLite database through the explicit Alembic maintenance path;
2. start Notify and Caddy;
3. verify `https://notify.goreecloud.com/healthz` returns the exact sanitized HTTP 200 payload;
4. prove the healthy state has emitted no alert;
5. prove the write-only/read-only/anonymous authorization boundaries;
6. stop the Notify application while leaving Caddy, ntfy, monitor, and subscriber running;
7. require the monitor to observe a server-side private-HTTPS failure through Caddy;
8. publish only the sanitized `GoreeCloud Notify DOWN` transition through the disposable write-only ntfy identity;
9. require the subscriber to observe exactly that DOWN event;
10. restart Notify and wait for the real database-aware container health check;
11. verify the private HTTPS health path recovers;
12. publish only `GoreeCloud Notify RECOVERED`;
13. require the subscriber to observe exact DOWN then RECOVERED order;
14. inspect runtime networks, source address, least-privilege container controls, and absence of host ports;
15. scan rendered Compose data, Docker inspection output, and runtime logs for generated token leakage;
16. destroy containers, volumes, generated credentials, and synthetic state.

This is monitoring-behavior evidence, not a claim that the disposable Python monitor is Uptime Kuma itself. The JSON contract defines the Uptime Kuma configuration that must later be registered and verified in the actual target environment.

## Independent outage-alert requirement

The temporary ntfy migration path does **not** satisfy the final independent Notify-down requirement.

During parallel migration, ntfy can provide useful secondary alert delivery because it is still running separately from GoreeCloud Notify. If both services ultimately share the same VPS, Docker host, Caddy instance, network dependency, storage dependency, or other material failure domain, that path is not independent enough to prove Notify-down delivery after ntfy retirement.

Before I retire ntfy, I must select, deploy, and test at least one out-of-band path that remains capable of reaching an administrator while GoreeCloud Notify itself is unavailable.

No final mechanism is approved by this PR. Candidate mechanisms remain subject to separate evaluation and may include:

- an approved external email path;
- a separately hosted notification service;
- a notification service in another failure domain;
- an approved independent mobile push path;
- another mechanism that can be demonstrated not to depend on the failed Notify runtime.

I will not mark `independent_out_of_band_alerting_proven` true until a controlled Notify outage is actually received through that independent path.

## Healthchecks boundary

GoreeCloud Healthchecks already has email alert capability for scheduled jobs and backup freshness. That is useful independent operational coverage for issue #23 backup/missed-backup failures.

I do not redefine Healthchecks as the GoreeCloud Notify service-availability monitor in this source slice. Uptime Kuma remains the planned availability monitor unless I separately approve and validate a different architecture.

## Target-environment cutover evidence

Before I register or repoint a live monitor I must record:

- the current ntfy monitor configuration read from Uptime Kuma immediately before change;
- the final Notify monitor ID/name and exact private HTTPS target;
- final monitor interval;
- final max retries;
- final retry interval;
- final request timeout;
- accepted status code policy;
- TLS verification policy;
- exact notification assignment;
- actual Uptime Kuma source address observed at Caddy;
- final Caddy allowlist value;
- proof that the monitor observes the final Caddy/private path instead of a backend socket;
- healthy/no-false-alert observation;
- controlled post-cutover DOWN detection;
- controlled RECOVERED detection;
- approved-administrator receipt of both state transitions;
- runtime/network/no-host-port evidence;
- protected credential owner/group/mode and least-privilege scope;
- rollback steps to restore the prior ntfy route and monitor state;
- independent out-of-band Notify-down delivery evidence.

## Rollback model

Monitoring migration is reversible.

If the Notify cutover is reversed, I will restore the ntfy Caddy/service route, restore or preserve the prior ntfy Uptime Kuma monitor state, remove or disable the unapproved Notify monitor, and verify ntfy health/recovery monitoring again before treating rollback as complete.

I will not delete the ntfy monitor merely because the new Notify monitor has been created. ntfy monitoring remains until the Notify monitor, final outage/recovery behavior, administrator receipt, and rollback procedure have been validated.

## Production boundary

This source slice does not:

- create a live Uptime Kuma monitor;
- change an existing Uptime Kuma notification assignment;
- modify production ntfy;
- modify production Caddy;
- change AdGuard Home, DNS, NetBird, firewall rules, or host ports;
- install a production monitoring token;
- deploy GoreeCloud Notify;
- prove administrator receipt;
- select or deploy the independent out-of-band path;
- approve ntfy retirement.

Issue #24 must remain open after source-controlled CI passes because the target-environment and independent-failure-domain evidence cannot be manufactured by repository tests.
