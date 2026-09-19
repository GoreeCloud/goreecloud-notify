# GoreeCloud Notify — Competitive Objectives

**Document Internal Version Number:** 2026.09.18.1  
**Document External Version Number:** 1.0.0  
**Status:** Active objective record  
**As of:** September 18, 2026

## Purpose

These are improvement and differentiation objectives, not claims that GoreeCloud Notify currently outperforms another product.

## Objectives

1. **Own the complete notification path.** Keep producer authentication, delivery state, inbox behavior, clients, recovery, and operational evidence in first-party GoreeCloud-controlled software.
2. **Provide stronger identity separation than anonymous topic publishing.** Prefer dedicated, least-privilege producer identities and explicit human-session boundaries.
3. **Provide durable user-visible state.** Treat notifications as persisted, reviewable delivery records rather than only transient messages.
4. **Maintain private-by-design deployment.** Support private DNS/Gateway/NetBird publication without requiring a public relay.
5. **Make migration safe.** Preserve only the compatibility surface required to migrate legacy producers, then keep the native API authoritative.
6. **Reduce notification-data exposure.** Minimize logs, browser/OS alert content, evidence bundles, and monitoring payloads.
7. **Make recovery measurable.** Require verified backup/restore and rollback evidence before production promotion.
8. **Avoid circular monitoring failure.** Require a separate failure-domain path for Notify-down alerts.
9. **Deliver consistent web/Linux/Android experiences.** Use one service contract while respecting platform-native accessibility and notification behavior.
10. **Integrate GoreeCloud platform systems truthfully.** Never convert naming, scaffolding, or local adapters into unsupported integration claims.
11. **Preserve open-source portability.** Keep deployment and migration paths understandable and independently operable.
12. **Make release state explicit.** Keep release-candidate source, production activation, and Stable qualification distinct and evidence-backed.

