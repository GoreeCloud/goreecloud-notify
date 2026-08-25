# GoreeCloud Notify — Glaze UI 1.4 conformance record

## Target and status

GoreeCloud Notify targets the current Stable **Glaze UI 1.4.0** release from the canonical `GoreeCloud/glaze-ui` design-system repository. The application source contains the current 1.4 semantic/form-factor foundation, but this document does **not** claim completed `Glaze UI 1.4 conformant` status or production Stable acceptance. Representative manual browser, operating-system, accessibility, and supported-profile acceptance remains mandatory.

This record applies to GoreeCloud-controlled user-facing Notify interfaces. Infrastructure-only components do not acquire a visual Glaze requirement merely because they support the application.

## Semantic contract

`frontend/src/glaze-contract.css` and the current responsive/resilience layers are the application-level bridge between Notify's established product palette and Glaze UI semantic roles. They preserve Notify's notification-focused composition while mapping semantic colors, spacing, radii, typography, surfaces, motion, target sizing, focus behavior, safe areas, adaptive ranges, and form-factor roles.

The application uses Canvas for the atmospheric application background, Solid for high-readability fallback/protected content, Raised for important content separation, selective Functional/Clear Glass where translucency materially helps hierarchy, and Overlay for attention-priority surfaces rather than applying maximum translucency everywhere.

## Adaptive and form-factor behavior

Notify uses the current Glaze adaptive ranges as window signals: Compact through 599 px, Medium 600–1023 px, Expanded 1024–1439 px, and Wide at 1440 px and above. Compact and Medium layouts transform navigation and workspace composition instead of merely shrinking desktop geometry. Expanded and Wide layouts preserve pointer/keyboard-oriented workspace behavior and larger-screen information balance.

The current source also includes native-client Glaze mapping for supported packaged clients. Platform-native clients must preserve Glaze semantic roles through appropriate native primitives rather than reproducing a scaled web shell. Source-level mappings do not substitute for real-device or representative form-factor acceptance.

## Accessibility and resilience

The source preserves a 44-pixel minimum actionable-target contract, visible keyboard focus, semantic labels/landmarks/status regions, skip navigation, System/Light/Dark appearance modes, reduced-motion handling, reduced-transparency and no-backdrop-filter fallbacks, forced-colors behavior, safe-area-aware layout, and operation when browser-local preference storage is unavailable. Automated browser checks cover representative signed-in and signed-out flows, but automated checks do not replace manual keyboard, screen-reader, zoom/reflow, contrast/readability, browser-permission, multi-tab, or operating-system notification acceptance.

## Privacy and dependency boundary

Glaze UI adds no analytics, tracking, advertising technology, remote fonts, remote icons, or third-party UI delivery. Notify uses local assets and local/system font fallbacks. Appearance and browser-alert preferences remain browser-local. Browser system alerts remain explicit opt-in and generic/redacted; private Delivery title, body, source, channel, and account details remain inside the authenticated inbox.

## Product and platform-system boundaries

Glaze UI remains the design language. Wardveil Security remains the evidence-backed security/protection identity, Privacy Shield remains the privacy-control identity/contract layer, and Everkeep remains the resilience/recovery identity. None of those systems substitutes for Glaze UI, and Glaze UI does not replace their technical authority.

## Automated evidence

`frontend/e2e/glaze-resilience.spec.ts`, `frontend/e2e/inbox.spec.ts`, browser-notification acceptance coverage, native-client validation, and `docs/glaze-ui-1.4-gates.json` provide source/automation evidence for current Glaze semantics and supported task flows. `docs/glaze-ui-1.4-gates.json` is fail-closed and keeps every acceptance-dependent gate explicit.

## Stable-release boundary

A `Glaze UI 1.4 conformant` claim is permitted only after every applicable current 1.4 gate is satisfied and representative supported-profile/task-flow acceptance is complete. Source integration, passing CI, responsive overflow checks, or a design-system Stable release do not automatically certify Notify. Until that evidence is complete, production Stable eligibility remains false and no exception is implied.
