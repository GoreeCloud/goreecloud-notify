# GoreeCloud Notify target monitoring evidence

## Purpose

I use `deploy/monitoring/validate_target_evidence.py` to validate the sanitized target-environment evidence required by the GoreeCloud Notify monitoring acceptance gate before I consider issue #24 complete.

The validator is read-only. It does not create or edit an Uptime Kuma monitor, change Caddy, change ntfy, install a credential, publish an alert, deploy Notify, or approve cutover. It validates a sanitized JSON record produced from real target observations after those approval-controlled actions are performed.

Repository/disposable monitoring readiness remains separate from target acceptance. A green GitHub Actions monitoring workflow proves the source pattern; it cannot manufacture the live Uptime Kuma registration, administrator receipt, Caddy source observation, rollback record, or independent failure-domain evidence.

## Why the validator exists

The source monitoring contract intentionally does not invent target-specific values for:

- maximum retries;
- retry interval;
- request timeout;
- live notification-assignment identifiers;
- the final observed Uptime Kuma source address;
- the final Caddy allowlist value;
- the independent out-of-band alert mechanism.

Those values must come from the actual target environment. The acceptance gate therefore requires them to be concrete and recorded instead of silently accepting a default, an omitted field, or a placeholder.

## Invocation

Run the validator against a local sanitized evidence file:

```text
python deploy/monitoring/validate_target_evidence.py /protected/path/notify-monitoring-evidence.json
```

A successful result exits zero and prints a single PASS line. Any missing, unexpected, unsafe, contradictory, or placeholder field fails closed with exit status 2.

The evidence file is an operational acceptance input, not a production secret store. Do not commit a live evidence file merely to make the validator pass.

## Required evidence structure

The root record must identify schema version 1, evidence kind `goreecloud-notify-monitoring-target-acceptance`, a timezone-aware capture timestamp, and `sanitized: true`.

The validator requires these sections.

### Notify monitor

The live monitor must record:

- a positive monitor ID;
- name `GoreeCloud Notify`;
- type `http`;
- URL `https://notify.goreecloud.com/healthz`;
- method `GET`;
- active state;
- 60-second interval;
- concrete maximum-retry, retry-interval, and request-timeout values;
- exact HTTP 200 acceptance;
- TLS verification enabled;
- at least one concrete notification-assignment identifier.

The retry and timeout values are deliberately not prescribed by this validator. They are accepted when they are concrete values from the live target record. Changing the monitor identity, health URL, interval, HTTP policy, or TLS requirement requires a deliberate source-contract change rather than an evidence-file workaround.

### Caddy and source path

The target evidence must record:

- that the Uptime Kuma request was observed at Caddy;
- the actual source IP address Caddy observed;
- the final Caddy monitor allowlist values;
- proof that the observed source is covered by that allowlist;
- final private HTTPS path verification;
- confirmation that monitoring did not bypass Caddy to use only a backend socket;
- database-aware `/healthz` verification.

This prevents a target record from claiming private-publication monitoring while actually probing an internal backend directly.

### State transitions and administrator receipt

The evidence must prove:

- a healthy period without false alerts;
- controlled DOWN detection with an HTTP failure at the final Caddy path;
- controlled recovery to HTTP 200;
- exact DOWN then RECOVERED ordering;
- an approved administrator received both transitions;
- the delivered content remained minimized.

Raw response bodies, application data, credentials, authorization material, environment dumps, or other protected diagnostics do not belong in the evidence record.

### ntfy preservation and rollback

The current ntfy monitor remains production rollback state during migration. The validator requires the target record to show that the ntfy monitor is still present and active and still matches the source-documented baseline:

- name `ntfy`;
- type `http`;
- URL `http://ntfy:80/v1/health`;
- 60-second interval;
- 3 retries;
- 60-second retry interval;
- 48-second request timeout;
- notification assignment present.

The evidence must also record that the rollback procedure exists, ntfy monitor state was preserved, Notify monitor removal/disable behavior is documented, and the ntfy route-restore procedure is documented.

If the live ntfy baseline legitimately changes before Notify cutover, update and revalidate the source contract deliberately instead of falsifying target evidence to match an obsolete value.

### Independent out-of-band Notify-down path

The temporary Uptime Kuma to ntfy migration path does not prove final independent outage alerting.

The evidence must record a concrete out-of-band mechanism that:

- is in a separate material failure domain;
- does not depend on GoreeCloud Notify;
- does not depend on the same Notify runtime host;
- was tested during a controlled Notify outage;
- delivered the Notify-down alert to an approved administrator.

The validator does not select the provider or mechanism. That remains an architecture/operations decision that must be validated in the real environment.

## Sensitive-data boundary

The validator rejects evidence fields whose names indicate reusable or protected material, including authorization values, cookies, CSRF values, database URLs, passwords, private keys, recovery codes, secrets, sessions, and tokens.

The schema is also strict about unexpected fields. If additional acceptance facts are needed, extend the source validator intentionally rather than attaching arbitrary raw diagnostic data to the evidence JSON.

The evidence should contain only the minimum facts required to prove the acceptance conditions. Protected screenshots, logs, provider configuration, or detailed operational artifacts may remain in their approved protected location and should be referenced through the normal GoreeCloud evidence/documentation process rather than copied into this sanitized validator input.

## Acceptance boundary

Passing this validator is necessary evidence for issue #24, but it does not by itself change production state or automatically close the issue. The administrator still needs to confirm that the evidence came from the intended target and that the corresponding approval-controlled operational records are retained.

No source test may set production monitoring, administrator receipt, or independent alerting to proven merely to obtain a green CI run. The source contract remains proposed-not-provisioned until the real production operation is explicitly performed and documented.
