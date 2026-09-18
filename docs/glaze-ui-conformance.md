# GoreeCloud Notify — Glaze UI 1.5.1 consumer adoption and conformance record

## Current required target

The current official Stable GoreeCloud design-system target is **Glaze UI 1.5.1**.

Shared Stable authority is defined by the canonical `GoreeCloud/goreecloud-glaze-ui` records including `contracts/v1.5.1/stable-scope.json`, `acceptance/v1.5.1-stable.md`, and `GLAZE_UI_V1_5.md`.

The reviewed V1.5 implementation anchor is `ee1032a0822ab8e103f8afe48e5c1859fde65cc9`. The V1.5.1 source-qualification anchor is `5b59d0e36950d737dba35b58ae58058684e0831b`.

Shared Stable status does not certify GoreeCloud Notify. Notify requires its own exact-revision implementation and acceptance for every supported user-facing surface.

## Current Notify source state

Notify now carries a repository-local **Glaze UI 1.5.1 source adoption candidate** for:

- web;
- Flutter Linux;
- Flutter Android.

The historical 1.3.0 mapping remains preserved in `docs/glaze-ui-v1.3-adoption.json` only as migration provenance.

The current source candidate does not claim completed Glaze conformance or production eligibility.

## Web mapping

The web client now resolves bounded presentation from actual application/runtime/accessibility state:

- viewport width drives single, stacked, or split presentation;
- Reduced Motion drives reduced presentation motion;
- Reduced Transparency, increased contrast, and Forced Colors take precedence over decorative optical treatment;
- actual Notify health state is represented as service capability state;
- actual SSE connection state is represented as realtime capability/connectivity presentation;
- actual browser Notification permission plus the user's local Notify opt-in are represented as system-alert capability state.

The resolver does not grant browser permission, authenticate users, change server state, execute fallback actions, or infer authorization. Browser notification permission is still requested only by the existing explicit user action.

The web source records the exact 1.5.1 shared anchors and exposes presentation/capability state through bounded document data attributes consumed by the repository-local CSS. Raw notification content and provider identity are not added to Glaze diagnostics or presentation metadata.

## Flutter Linux and Android mapping

The Flutter client now identifies Glaze UI 1.5.1 and binds the same reviewed/shared qualification anchors.

Native presentation resolution uses Flutter `MediaQuery` state for:

- pane/layout mode;
- large-text-aware density;
- high-contrast material fallback;
- reduced-animation preference.

`GlazeChrome` becomes solid when the authoritative Flutter accessibility context requests high contrast rather than forcing translucent material.

Android persistent-system-alert state is recorded only from actual platform/plugin outcomes:

- previously enabled persistent alerts → available;
- permission denial → restricted;
- failed persistent-alert activation → temporarily unavailable;
- not-yet-established permission → unknown.

The Glaze presentation layer never grants permission. Permission is still requested only inside the user-initiated Enable flow.

## Authority boundaries

Glaze UI is presentation and interaction authority only. It does not infer authorization, create consent, grant permission, determine authenticated identity, redefine Privacy Shield requirements, reinterpret Wardveil Security state, manufacture service health, create GoreeCloud Policy decisions, or alter GoreeCloud Observability evidence.

Provider/capability state used by this consumer mapping is derived only from the owning application, browser/runtime, Flutter runtime, or platform API already responsible for that state.

## Accessibility and resilience

Existing resilient fallbacks remain in force, including:

- no-backdrop-filter fallback;
- Reduced Transparency;
- Reduced Motion;
- increased contrast;
- Forced Colors;
- responsive layout;
- large-text/native density mapping;
- minimum target-size floors.

Automated browser/native source evidence does not substitute for representative manual keyboard, screen-reader, zoom/reflow, operating-system notification, physical-device, or visual-excellence acceptance.

## Platform-system boundary

The root `goreecloud.platform.yaml` uses Platform Contract 0.4 and declares all nine Integral Platform Systems. Glaze UI remains `applicable-migration-required` until application-specific acceptance is complete.

Other blocked platform systems remain independent blockers. Source adoption of Glaze UI does not satisfy Manager, Privacy Shield, Wardveil Security, Everkeep, Mesh, Identity, Policy, or Observability acceptance.

## Remaining acceptance

The exact candidate still requires applicable:

- representative browser/OS accessibility and visual acceptance;
- Flutter Linux native accessibility and performance acceptance;
- Android physical-device, accessibility, background-delivery, posture/rotation where applicable, and signing acceptance;
- application-specific performance-budget evidence;
- known-good application rollback validation;
- governed Glaze consumer-registry acceptance;
- exact-revision production approval.

Until those gates are accepted, Notify must not claim current Glaze UI conformance, Stable product qualification, complete platform conformance, or production eligibility based on source adoption alone.
