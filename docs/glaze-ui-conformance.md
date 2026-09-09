# GoreeCloud Notify — GLAZE UI V1.3 migration and conformance record

## Current target and exact authority

GoreeCloud Notify now targets current Official Stable **GLAZE UI V1.3 / `1.3.0` — Adaptive Resonance** from the canonical `GoreeCloud/goreecloud-glaze-ui` repository. The exact shared source integration anchor used for this repository-local migration is `fc7cc91d2eace8da2371371c2855c24cbcb326a1`.

This repository records a **migration candidate**, not completed Glaze UI conformance. V1.3 being Stable and consumer-eligible does not certify Notify. Repository-local rendered/native, accessibility, adaptive/form-factor, workflow, performance, rollback, and production acceptance remain independent gates.

Historical pre-reset 1.4 and 2.1 records are source-control provenance only. They do not override the current V1.3 lifecycle authority and are not reinterpreted as V1.3 evidence.

## Web source mapping

`frontend/src/glaze-contract.css`, `frontend/src/main.tsx`, and `frontend/index.html` now identify `1.3.0` consistently. The web mapping preserves Notify's established notification-focused composition while mapping canvas, surface, semantic color, spacing, radii, motion, focus, adaptive density, and bounded material roles to the current V1.3 target.

V1.3 inherits the V1.2 ergonomic floors used here: ordinary actionable targets are at least 48 px, with 56 px source hooks for Touch Assistance and far-view contexts. Existing selectors that previously overrode the generic target rule are explicitly bound to the V1.3 target token so rendered controls cannot silently remain at the historical 44/46 px floor.

The web source also keeps fail-soft no-backdrop-filter behavior, Reduced Transparency, Reduced Motion, increased-contrast, Forced Colors, large-text/reflow, compact-layout, and wide-layout source paths explicit. These source paths require representative acceptance; their presence does not manufacture assistive-technology or physical-device evidence.

## Flutter-native source mapping

`client/lib/glaze_theme.dart` records the same `1.3.0` target and exact shared source anchor. Shared roles map to Flutter/Material primitives rather than reproducing the web shell. The native mapping carries the same 48 px ordinary and 56 px assisted/far-view target floors and keeps translucent material bounded to interaction chrome/emphasis.

Linux and Android packaging/build evidence does not constitute native Glaze acceptance. Android physical-device behavior, accessibility, system appearance, background-delivery interaction, production signing, and representative performance remain separate product gates.

## Accessibility and resilience

The existing browser acceptance suite remains authoritative only for what it actually executes. `frontend/e2e/glaze-resilience.spec.ts` now verifies the V1.3 source identity and the effective 48/56 px target tokens in the rendered web application. Automated Axe/browser coverage is useful evidence but does not replace manual keyboard, screen-reader, 200% zoom/reflow, contrast/readability, operating-system notification, or physical-device acceptance.

Accessibility and task completion outrank expressive treatment. Adaptive color, translucency, material depth, or motion must never be the sole carrier of notification state, severity, focus, error, success, warning, progress, or interaction affordance.

## Platform-system boundary

Glaze UI owns presentation and interaction contracts. Wardveil Security remains the security/protection authority, Privacy Shield remains the privacy-control authority, Everkeep remains the continuity/recovery authority, GoreeCloud Identity remains the identity authority, and GoreeCloud Mesh remains the coordination/capability authority. This migration does not imply those integrations are complete or accepted.

The root `goreecloud.platform.yaml` is the machine-readable Platform Contract declaration. `docs/platform-conformance.json` remains the repository-local detailed status record. Both remain fail-closed and preserve unresolved platform and production blockers.

## Rollback and Stable boundary

GLAZE UI V1.2 / `1.2.0` is the immediately preceding shared rollback baseline. A production migration must still bind a known-good Notify revision, verify rollback on Notify's own integration path, and obtain explicit acceptance for the exact consumer revision.

Until all applicable gates in `docs/glaze-ui-v1.3-adoption.json` are complete, Notify must not claim `Glaze UI V1.3 conformant`, production Stable qualification, or completed platform conformance merely because source integration and automated CI pass.
