# GoreeCloud Notify — Glaze UI 2.1 Adoption Candidate

## Status

- Required current Stable design-system release: **Glaze UI 2.1.0**
- Canonical source: `GoreeCloud/goreecloud-glaze-ui`
- Stable release tag: `v2.1.0`
- Stable promotion revision: `c49113eb8b93c267613fdf1bbca1f814495acad7`
- Repository status: **Adoption Candidate**
- Current-Stable conformance claim: **false**
- Production Stable eligibility from this gate: **false**

Notify now carries repository-local Glaze UI 2.1 source mappings for its web application and Flutter-native client. Those mappings are migration evidence and do not by themselves establish rendered, browser/OS, native accessibility, physical-device, performance, or human Visual Excellence acceptance.

The previous Glaze UI 1.4 ledger remains historical migration and audit evidence only. It no longer defines the active consumer target.

## Material and interaction mapping

Notify preserves its notification-focused information architecture while adopting the current Stable hierarchy:

**Canvas → Surface → Soft Glaze → Glaze → Deep Glaze → Live Glaze**

Durable notification content, message bodies, provenance, and account-sensitive reading surfaces remain solid by default. Glazed material is reserved for navigation, filters, controls, transient interaction, and bounded live/attention-priority surfaces. The migration does not make private Delivery state decorative or move producer authority into the presentation layer.

The web bridge is `frontend/src/glaze-contract.css`. The native bridge is `client/lib/glaze_theme.dart`; it maps shared semantics into Flutter-native primitives rather than embedding or scaling the web shell.

## Accessibility and density

The web and native source contracts now use a **48 px/dp general effective target floor**. They also define a **56 px/dp Touch Assistance floor**, with a separate 56 px/dp far-view contract for any future accepted far-view surface.

The web layer includes explicit source hooks for Large Text, Touch Assistance, and far-view rendering; Solid material fallbacks for reduced transparency and unsupported backdrop filtering; reduced-motion handling; increased-contrast resolution; and forced-colors behavior. Compact density yields to a readable effective density when the Large Text rendering state is active.

These source hooks do not prove that every supported browser, operating system, native platform, or device correctly resolves the relevant user preference. Representative 200% Large Text, Touch Assistance, keyboard, screen-reader, contrast, reduced-motion, reduced-transparency, and forced-colors acceptance remains mandatory.

## Native client boundary

`client/lib/glaze_theme.dart` records the 2.1 Stable version and material vocabulary and raises native target floors without replacing Flutter/Android platform semantics. Physical-device Android acceptance, native accessibility behavior, background-delivery behavior, signing/installation validation, and performance remain separate release gates.

A working web implementation must never be used as evidence that a native device behavior was accepted, and vice versa.

## Privacy and platform authority boundaries

Glaze UI standardizes presentation only. Notify continues to treat the following systems as authoritative for their own state:

- **Wardveil Security** for security/protection state and evidence.
- **Privacy Shield** for privacy-control state and evidence.
- **Everkeep** for continuity/recovery state and evidence.
- **GoreeCloud Identity** for identity/authentication state where integrated.
- **GoreeCloud Mesh** for coordination/connectivity state where integrated.

Appearance and browser-alert preferences remain local to their relevant client context unless a separate authoritative synchronization contract exists. Glaze UI adds no analytics, advertising, remote fonts, remote icons, or tracking requirement.

## Fail-closed evidence

`docs/glaze-ui-2.1-adoption.json` is the active machine-readable adoption ledger. It pins the exact current Stable release and records unresolved rendered, accessibility, native, physical-device, performance, platform-authority, and central-registry gates. `backend/tests/test_glaze_ui_2_1_adoption.py` verifies the exact release provenance, web material hierarchy, target floors, accessibility hooks, native version/target mapping, authority boundary, and fail-closed production posture.

`docs/glaze-ui-1.4-gates.json` remains historical evidence only.

## Remaining acceptance before a current-Stable claim

Notify must still complete rendered web task-flow review; browser/OS keyboard, screen-reader, reduced-motion, reduced-transparency, increased-contrast, forced-colors, 200% Large Text, and Touch Assistance acceptance; Flutter-native accessibility acceptance; application-specific Material Budget/performance evidence; physical-device Android review; human Visual Excellence review; and a reviewed central Glaze consumer-registry entry.

Until those gates are complete, the truthful status is **Glaze UI 2.1 Adoption Candidate**, not `aligned-current-stable` and not production-accepted conformance.
