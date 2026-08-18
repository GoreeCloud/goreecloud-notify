# GoreeCloud Notify Application Identity

## Purpose

GoreeCloud Notify uses one canonical product identity across every supported or future client surface. This prevents the web application, Linux packaging, Android packaging, shortcuts, launchers, manifests, and future platform integrations from drifting into separate visual identities.

The authoritative source artwork is:

`frontend/public/brand/goreecloud-notify-icon.svg`

The machine-readable distribution contract is:

`packaging/application-identity.json`

## Canonical icon

The Notify icon is a product-specific Glaze UI mark rather than the generic GoreeCloud platform logo. Its primary symbol combines a notification bell, a distinct N-shaped delivery pulse, and an unread/status point inside a Glaze blue product tile.

The source is a local scalable SVG with no remote fonts, remote images, scripts, tracking resources, embedded raster content, or external runtime dependency. Platform-specific derivatives may change rasterization, safe-area padding, masking, monochrome treatment, or launcher corner treatment when the target platform requires it, but they must preserve the same underlying symbol and product identity.

## Web and installable web surface

The web application uses the canonical SVG directly as its browser favicon. `frontend/public/manifest.webmanifest` also references the same source for the installable web identity and declares it suitable for ordinary and maskable presentation.

Vite copies `frontend/public/` into the immutable production frontend artifact, so the favicon, manifest, and canonical source artwork are included in the existing production build rather than loaded from a third party.

## Linux AppImage contract

Linux desktop/AppImage packaging must derive its launcher and package icon assets from `frontend/public/brand/goreecloud-notify-icon.svg`.

A future Linux client may generate the raster or freedesktop sizes required by its packaging toolchain, but it must not substitute a different logo, recolor a generic GoreeCloud mark as the sole distinction, or maintain a separate editable master artwork file.

This contract does not claim that a Linux/AppImage client is implemented, accepted, signed, or production-ready. A future desktop client still requires an approved application architecture, authentication/session model, secure update and packaging design, Glaze UI acceptance, release validation, and target-system testing before it may be classified as supported or Stable.

## Android APK contract

Android APK or AAB packaging must derive launcher/adaptive icon assets from the same canonical SVG.

Android-specific foreground/background separation, masking, monochrome launcher treatment, density-specific rasterization, and safe-zone adjustments are allowed when they are generated as platform adaptations of the canonical mark. They must not change the underlying notification-bell and N-pulse identity.

This contract does not claim that an Android client is implemented, accepted, signed, or production-ready. The project specification continues to define web first and Android next. Android implementation still requires an approved mobile architecture, authentication and token/session handling appropriate to a native client, notification-delivery design, secure storage, Glaze UI adaptation, signing/recovery controls, and real-device acceptance.

## Security and privacy boundary

Application identity assets are presentation resources only. They do not weaken or replace Wardveil Security, application authentication, authorization, CSRF protection, producer-token controls, private publication, backup/recovery, monitoring, or other technical security authorities.

The repository regression suite must reject canonical icon changes that introduce executable SVG content, embedded external images, remote resource references, data URLs, or cross-platform source divergence.

## Change control

Any future change to the canonical icon must be reviewed as an application-wide identity change. The web favicon, web manifest, Linux packaging contract, Android packaging contract, repository documentation, release metadata, and any implemented platform derivatives must be updated or regenerated together from the same canonical source.
