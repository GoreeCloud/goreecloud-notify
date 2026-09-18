# GoreeCloud Notify — Glaze UI current-Stable adoption and conformance record

## Current required target

The current official Stable GoreeCloud design-system target is **Glaze UI 1.5.1**.

Shared Stable authority is defined by the canonical `GoreeCloud/goreecloud-glaze-ui` records including `contracts/v1.5.1/stable-scope.json`, `acceptance/v1.5.1-stable.md`, and the V1.5 family contract. The shared reviewed implementation anchor is `ee1032a0822ab8e103f8afe48e5c1859fde65cc9`; the V1.5.1 source-qualification anchor is `5b59d0e36950d737dba35b58ae58058684e0831b`.

Shared Stable status does not certify GoreeCloud Notify. Notify requires its own exact-revision implementation and acceptance for every supported user-facing surface.

## Current Notify source state

The current Notify reconciliation candidate still contains repository-local web and Flutter source mappings for historical Glaze UI **1.3.0**. Those mappings are preserved as migration evidence in `docs/glaze-ui-v1.3-adoption.json` and related source/tests.

They are **not current conformance evidence**. Notify is therefore Glaze UI migration-required and production-blocked until 1.5.1 is substantively implemented and accepted.

Do not relabel the existing 1.3.0 CSS, browser metadata, or Flutter theme as 1.5.1 merely by changing version strings. Current adoption must incorporate the applicable V1.5 presentation/authority model and then produce fresh application-specific evidence.

## Required 1.5.1 adoption boundary

Notify's supported surfaces are:

- web;
- Flutter Linux;
- Flutter Android.

Fresh adoption and acceptance must cover, as applicable:

- contextual and capability-aware presentation without manufacturing authorization or capability truth;
- accessibility precedence and graceful reduced-effect fallbacks;
- stable primary actions and task continuity;
- responsive/adaptive layout and density;
- semantic state and status communication;
- material, depth, motion, focus, and interaction behavior;
- browser/OS and native accessibility;
- large text, reflow, contrast, Forced Colors, Reduced Motion, and Reduced Transparency;
- representative performance against the approved Glaze UI performance budget;
- Android device/posture behavior where applicable;
- application-specific visual excellence;
- known-good rollback;
- exact-revision repository-local acceptance and production approval.

The current requirement ledger is `docs/glaze-ui-v1.5.1-adoption.json`.

## Authority boundaries

Glaze UI is presentation and interaction authority only. It does not infer authorization, permission, consent, security state, privacy permission, identity truth, policy decisions, continuity state, Mesh registration, or operational health.

Wardveil Security, Privacy Shield, Everkeep, GoreeCloud Identity, GoreeCloud Policy, GoreeCloud Observability, GoreeCloud Mesh, and GoreeCloud Manager retain their respective authority domains.

## Platform-system boundary

The transitional root `goreecloud.platform.yaml` uses the currently supported machine-readable contract and remains nonconformant. The v3.0 nine-system evaluation is recorded in `docs/platform-conformance.json`.

A legacy seven-system machine declaration must not be interpreted as complete v3.0 platform conformance. GoreeCloud Policy and GoreeCloud Observability remain explicit blockers until supported and accepted.

## Stable and production boundary

Until the 1.5.1 ledger's applicable gates are implemented and accepted for the exact Notify revision, Notify must not claim:

- current Glaze UI conformance;
- Stable product qualification;
- complete platform conformance;
- production eligibility based on UI source alone.

Historical 1.3.0 evidence remains useful migration provenance only.
