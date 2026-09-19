# GoreeCloud Notify — Repository Specifications

**Document Internal Version Number:** 2026.09.18.1  
**Document External Version Number:** 1.0.0  
**Status:** Current repository-coupled specification  
**As of:** September 18, 2026  
**Repository:** `GoreeCloud/goreecloud-notify`  
**Central project record:** `GoreeCloud/Projects/Project Specification — Notify.docx`

## Purpose

This file records the current source-coupled specifications for GoreeCloud Notify. It does not replace the central project specification, GoreeCloud governance, release evidence, or target-environment acceptance records.

Where this file and live implementation differ, the verified repository/runtime state controls factual current-state claims and this file must be reconciled.

## Product role

GoreeCloud Notify is the GoreeCloud-native centralized notification-delivery application. The retired ntfy service is historical/recovery context only.

The current source line is a **release candidate**. Source integration does not imply production activation.

## Current product version and surfaces

- Platform Contract product version: `0.2.0`.
- Web application: React/TypeScript.
- Backend service: FastAPI with SQLite persistence.
- Native clients: Flutter Linux and Flutter Android.
- Supported API family: `/api/v1`.
- Authenticated realtime delivery: Server-Sent Events at `/api/v1/inbox/stream`.
- Bounded authenticated legacy producer compatibility: `/{topic}`.

## Core application requirements

Notify must provide:

- authenticated human sessions;
- scoped producer identities and credentials;
- native notification ingestion;
- subscription fanout;
- durable notification and delivery state;
- read/acknowledgement state;
- authenticated realtime inbox delivery;
- browser system-alert presentation that does not silently expose sensitive notification content;
- administrative controls appropriate to the current source line;
- health/readiness evidence through `/healthz`;
- backup, restore, migration, and target-preflight tooling;
- exact-revision release and target evidence.

## Data and identity boundaries

SQLite is the current persistent application database for notification, delivery, user/session, producer, audit, and security state.

Reusable credentials, active secrets, private keys, session values, CSRF values, recovery material, and production environment files must not be committed.

Current source uses application-local human-session and producer-identity controls. Accepted GoreeCloud Identity integration remains blocked and must not be inferred from local authentication.

## Notification-delivery contract

Producer delivery must remain authenticated, scoped, bounded, and idempotency-aware where the applicable API contract requires it.

The ntfy-compatible endpoint exists only as a constrained migration surface for legacy producers. It is not evidence that ntfy remains an active dependency.

## Privacy and observability

Notify must minimize operational evidence and avoid placing authorization headers, cookies, session values, raw reusable credentials, raw notification bodies, or other unnecessary sensitive data into routine logs or monitoring evidence.

Privacy Shield and GoreeCloud Observability source candidates do not establish central/runtime acceptance.

## Security

Wardveil Security presentation does not replace application security controls.

Production-relevant requirements include:

- secure session handling;
- CSRF protection where applicable;
- producer-token authorization;
- input validation;
- secure transport;
- private publication;
- no public backend host port;
- least-privilege runtime identity;
- protected runtime configuration;
- target vulnerability/security acceptance;
- secure backup/recovery handling.

## Continuity and recovery

Backup and restore are mandatory before production acceptance.

The approved target must establish:

- backup destination/repository;
- schedule and retention;
- protected independent recovery credentials;
- missed/failed-backup alerting;
- alternate-location restore;
- exact-revision restore validation;
- security-state reconciliation after restore;
- tested rollback/recovery to a previous known-good Notify release.

The retired ntfy service is not the ordinary rollback target.

## Monitoring and independent outage alerting

GoreeCloud Monitor is the intended primary availability monitor only after Monitor is independently production-accepted.

Notify production acceptance requires a separately tested Notify-down path that:

- does not depend on Notify itself;
- does not depend on the same runtime host;
- occupies a separate material failure domain;
- reaches an approved administrator during a controlled outage test.

## Glaze UI

The current required Stable design-system target is Glaze UI **1.5.1**.

Web, Flutter Linux, and Flutter Android source contain a 1.5.1 source-adoption candidate with presentation-only authority.

Application-specific browser/native accessibility, physical-device, performance, rollback, consumer-registry, and production acceptance remain required.

## Integral Platform Systems

The root `goreecloud.platform.yaml` is the machine-readable Platform Contract 0.4 declaration.

Current platform-system state is fail-closed:

- GoreeCloud Manager: applicable / blocked.
- Privacy Shield: source adapter candidate / runtime-central acceptance blocked.
- Wardveil Security: source adoption evidence / target-runtime acceptance blocked.
- Everkeep: source acceptance-policy candidate / target restore acceptance blocked.
- Glaze UI: 1.5.1 source-adoption candidate / application acceptance blocked.
- GoreeCloud Mesh: applicable / blocked.
- GoreeCloud Identity: applicable / blocked.
- GoreeCloud Policy: applicable / blocked.
- GoreeCloud Observability: applicable / blocked.

## Production acceptance boundary

Production activation remains blocked until applicable evidence verifies:

- exact target runtime and image;
- backup and alternate-location restore;
- private Gateway/DNS/NetBird publication;
- target security acceptance;
- active-producer migration;
- end-to-end delivery and realtime behavior;
- accepted primary monitoring;
- independent Notify-down alerting;
- manual browser/OS/native acceptance;
- remaining platform-system acceptance;
- rollback/recovery;
- explicit production approval.

