# GoreeCloud Notify — Privacy Policy

**Document Internal Version Number:** 2026.09.18.1  
**Document External Version Number:** 1.0.0  
**Status:** Repository privacy policy for the current release-candidate source  
**As of:** September 18, 2026

## Scope

This policy describes privacy-relevant behavior implemented or required by the current GoreeCloud Notify source. A deployment operator remains responsible for the actual environment, accounts, retention, backups, and lawful use of the deployed service.

## Data Notify may process

Depending on deployment and use, Notify may process:

- account identifiers and account state;
- authentication/session state;
- producer identities and authorization metadata;
- notification titles, bodies, severity, channel/subscription metadata, and timestamps;
- delivery/read/acknowledgement state;
- user preferences and subscriptions;
- minimized security/audit events;
- backup/recovery state and migration metadata necessary to operate the service.

## Purpose

The application processes this data to:

- authenticate users and producers;
- accept authorized notification events;
- deliver notifications to intended users/subscriptions;
- maintain inbox and delivery state;
- support realtime synchronization;
- provide administrative/security controls;
- detect operational failures;
- support backup, restore, migration, and incident investigation.

## Data minimization

Notify is designed to minimize operational evidence.

Routine application/monitoring evidence must not intentionally include reusable credentials, authorization headers, cookies, raw session values, recovery codes, private keys, or other secret material.

Monitoring and diagnostics should use bounded status/evidence rather than copying full notification content when not required.

## Browser and operating-system alerts

Browser/OS alerts can expose information outside the application window.

Permission must be user initiated where the platform requires permission.

Alert content should be minimized according to the deployment's privacy requirements. The in-application inbox remains the authoritative delivery surface.

## Retention and deletion

Durable application state is retained according to the current application behavior and deployment policy.

Deletion controls implemented by the application must be honored, but complete production retention/Privacy Shield acceptance remains a separate platform gate.

Backups may retain data for their approved recovery period and must be protected according to the recovery policy.

## Sharing and external services

The source does not treat an external notification relay as a required production dependency.

Data may be transmitted to infrastructure and clients that are deliberately configured as part of the deployment, including the approved private gateway/network and user devices.

Any additional third-party service introduced by a deployment operator is outside this repository policy unless explicitly documented and approved.

## Security safeguards

Privacy depends on technical security controls including authentication, authorization, TLS, private publication, protected producer credentials, secure sessions, least-privilege runtime configuration, backup protection, and target security validation.

## Platform privacy status

A repository-local Privacy Shield adapter candidate exists, but central/runtime Privacy Shield acceptance is not complete. This policy must not be used to claim complete Privacy Shield conformance.

## User/admin responsibilities

Users should avoid placing reusable secrets in notification content.

Administrators must protect application data, backups, runtime configuration, producer credentials, and access to the private deployment.

## Changes

Material privacy behavior changes must update this file, applicable project documentation, and Privacy Shield evidence in the same governed workflow.

