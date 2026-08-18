# GoreeCloud Notify — Glaze UI conformance

## Target

GoreeCloud Notify targets **Glaze UI 1.0.0** from the canonical `GoreeCloud/glaze-ui` design-system repository.

This record applies to the GoreeCloud-controlled web interface. It does not claim that infrastructure-only components have a visual Glaze UI requirement.

## Semantic contract

`frontend/src/glaze-contract.css` is the application-level semantic bridge between Notify's established product palette and Glaze UI 1.0 roles. It records the shared target, spacing, radius, focus, motion, target-size, semantic color, and surface vocabulary without replacing Notify's successful notification-focused composition.

The application intentionally preserves its existing GoreeCloud identity while mapping the following roles:

- Canvas → Notify atmospheric application background.
- Solid → high-readability fallback and protected content surfaces.
- Raised → summary and important content separation.
- Glaze → primary shell, sidebar, and major application regions using selective translucency.
- Overlay → reserved for future dialogs, menus, and other attention-priority surfaces rather than applying maximum translucency everywhere.

## Accessibility and resilience

The web application preserves or enforces:

- a 44-pixel minimum actionable target contract;
- visible keyboard focus with a three-pixel focus treatment and two-pixel offset;
- semantic labels, status regions, landmarks, and skip navigation;
- system, light, and dark appearance modes;
- reduced-motion behavior;
- reduced-transparency and no-backdrop-filter solid fallbacks;
- forced-colors behavior for critical controls and status presentation;
- operation when browser-local preference storage is unavailable;
- automated WCAG A/AA browser checks for representative signed-in and signed-out flows.

## Adaptive layout

Notify uses the Glaze UI adaptive ranges as the application contract:

- Compact: through 599 px;
- Medium: 600–1023 px;
- Expanded: 1024–1439 px;
- Wide: 1440 px and above.

Medium and Compact layouts transform navigation and workspace composition instead of only shrinking the Expanded layout. Wide layouts increase workspace breathing room and notification/detail balance.

## Privacy and dependency boundary

Glaze UI does not add analytics, tracking, advertising technology, remote fonts, remote icons, or third-party UI delivery. Notify uses local application assets and system/local font fallbacks. Appearance and system-alert preferences remain browser-local.

Browser system alerts remain explicit opt-in. Their operating-system content is intentionally generic and redacted; private Delivery title, body, source, channel, and account details remain in the authenticated Notify inbox.

## Release-state presentation

The frontend consumes `/api/v1/meta` release metadata for version, release stage, build revision, and production-acceptance status. User-facing status text must not present obsolete development milestones when the running backend identifies itself as a release candidate or production build.

## Automated conformance evidence

`frontend/e2e/glaze-resilience.spec.ts` validates the recorded Glaze target, core semantic contract values, minimum target size, Auto light/dark behavior, and browser-storage resilience.

`frontend/e2e/inbox.spec.ts` validates representative authenticated Glaze UI behavior, keyboard skip navigation, dark appearance, Compact reflow without horizontal document overflow, and automated WCAG A/AA checks.

`frontend/e2e/browser-notifications.spec.ts` validates explicit permission opt-in, privacy-preserving alert content, fail-closed denial behavior, and external browser-permission reconciliation.

## Manual stable-release acceptance

Automated conformance is necessary but does not replace manual stable-release acceptance. Before production stable classification, record representative Compact and Expanded visual review in light and dark appearances, practical contrast/readability, keyboard/focus behavior, assistive-technology sanity, and final browser/OS behavior. Any unmet Glaze UI requirement requires an explicit approved exception; no permanent exception is declared by this document.
