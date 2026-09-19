# GoreeCloud Notify — Repository Notes

**Document Internal Version Number:** 2026.09.18.1  
**Document External Version Number:** 1.0.0  
**Status:** Current repository-maintenance notes  
**As of:** September 18, 2026

## Current source state

- ntfy was retired from `goreecloud-vps-01` on September 18, 2026.
- Post-retirement source/platform reconciliation is integrated.
- Glaze UI 1.5.1 source adoption is integrated.
- The post-retirement monitoring acceptance contract is integrated.
- The repository remains a release-candidate source line.
- Production acceptance remains false.

## Current production blockers

- live VPS runtime readback and exact image/revision verification;
- target backup and alternate-location restore;
- private Gateway/DNS/NetBird validation;
- accepted GoreeCloud Monitor deployment;
- independent Notify-down alert path outside Notify and the same host;
- migration of actually active legacy producers;
- browser/OS/native manual acceptance;
- Android physical-device/signing/background-delivery acceptance;
- remaining Integral Platform System acceptance;
- rollback/recovery exercise;
- explicit production approval.

## Documentation authority

- Central project specification: `GoreeCloud/Projects/Project Specification — Notify.docx`.
- Central changelog: `GoreeCloud/Changelogs/Change Log — Notify.docx`.
- Repository roadmap: `FEATURE-ROADMAP.md`, synchronized with the canonical Drive roadmap.
- This repository is authoritative for source-coupled implementation documentation.

## Historical evidence

- V1.3 Glaze records are historical migration provenance.
- ntfy compatibility code is a migration surface, not evidence of a live ntfy dependency.
- The former native Google Doc changelog is superseded by the canonical DOCX changelog in Drive.

## Maintenance rule

Keep source status, platform conformance, roadmap state, and target-acceptance boundaries synchronized with verified implementation. Do not convert planned, partial, or unverified production work into completion claims.

