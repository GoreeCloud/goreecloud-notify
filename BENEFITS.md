# GoreeCloud Notify — Benefits

**Document Internal Version Number:** 2026.09.18.1  
**Document External Version Number:** 1.0.0  
**Status:** Current supportable benefit record  
**As of:** September 18, 2026

## Purpose

This file records benefits supported by the current GoreeCloud Notify design and source. It does not make production-readiness claims.

## Benefits

- **First-party control:** notification ingestion, delivery, inbox state, clients, and operational evidence remain under GoreeCloud-controlled source and deployment.
- **Private self-hosting:** the architecture is designed for private publication and does not require a public notification relay.
- **Scoped producers:** producer identities can be separated by purpose instead of sharing one broad write credential.
- **Durable inbox state:** notification and delivery state is persisted rather than existing only as transient push traffic.
- **Realtime delivery:** authenticated SSE provides a low-latency inbox update path with reconnection/replay handling.
- **Cross-platform access:** web, Linux, and Android clients share the same service contract.
- **Migration continuity:** the bounded ntfy-compatible endpoint provides a controlled path for legacy producer migration without keeping ntfy as an active service dependency.
- **Privacy-oriented presentation:** browser/native alert handling is designed to minimize unnecessary exposure of notification content.
- **Recovery focus:** backup, restore, target preflight, and rollback requirements are part of the product acceptance model.
- **GoreeCloud integration path:** the source explicitly evaluates Glaze UI, Wardveil Security, Privacy Shield, Everkeep, Manager, Mesh, Identity, Policy, and Observability without claiming integrations that are not accepted.
- **Fail-closed production boundary:** source readiness, deployment, monitoring, and production approval remain distinct states.

