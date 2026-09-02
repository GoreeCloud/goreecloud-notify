# GoreeCloud Notify dependency license review

## Decision

Current and future GoreeCloud-owned GoreeCloud Notify source is licensed prospectively under the **GNU Affero General Public License, version 3 only (`AGPL-3.0-only`)** beginning with the repository relicensing integration that contains this review.

This is a prospective source-license change. GoreeCloud Notify `v0.2.0`, published from commit `dd22a7ad0765c8ca62b401749265594bb0a06e23`, was distributed under the MIT License. That release and copies previously distributed under MIT retain their MIT permissions. See `LICENSE-NOTICE.md`.

AGPL-3.0-only is selected for the original GoreeCloud-owned network/server application so modified network-service deployments receive the source-availability reciprocity expected for this service. Dependencies and separately licensed components are not relicensed as GoreeCloud-owned source.

The current source grant is stored at the repository root in `LICENSE`. The production image copies both `LICENSE` and `LICENSE-NOTICE.md` into `/app` and records `org.opencontainers.image.licenses=AGPL-3.0-only`.

## Automated dependency evidence

The repository contains `tools/dependency_license_inventory.py`.

The tool:

- reads the complete exact Python dependency closure from `backend/constraints.txt`;
- resolves each pinned Python package from the installed CI environment;
- verifies that the installed Python version matches the exact constraint;
- records installed Python license metadata;
- reads every npm dependency entry from `frontend/package-lock.json`;
- records exact npm package versions and lockfile license metadata;
- distinguishes development-only and optional npm entries;
- reports unknown license metadata rather than guessing;
- emits Markdown or JSON;
- fails in strict mode when resolution, version, lockfile, or license metadata is incomplete.

CI runs the strict inventory after the constrained backend environment is installed. A green strict inventory remains required after the application-license change.

The native Flutter client is also a first-party GoreeCloud component. Its direct Flutter/plugin dependencies remain separately licensed upstream components and are not converted to AGPL by the repository license.

## Review conclusion

The reviewed dependency boundary does not prevent AGPL-3.0-only licensing of the original GoreeCloud-owned Notify source.

Runtime application dependencies are consumed as separately maintained third-party packages and retain their own licenses. The current Python runtime closure uses the established FastAPI, SQLAlchemy, Uvicorn, Alembic, Argon2, Pydantic/Starlette, and supporting package ecosystem. The browser runtime uses React/ReactDOM. Development/browser tooling, including Playwright/Axe tooling, remains separately licensed and is not part of the production runtime image merely because it is present in the source tree.

The strict inventory previously completed without unknown Python/npm license metadata or dependency-version drift. The same strict check must remain green on the exact relicensing head.

No third-party package is relicensed as GoreeCloud-owned code. If vendored, copied, or separately licensed source is introduced later, its required copyright/license notices and applicable terms must remain preserved.

## Distribution boundary

For current source distribution:

- keep the root `LICENSE` file containing the `AGPL-3.0-only` grant;
- keep `LICENSE-NOTICE.md` so the published `v0.2.0` MIT grant and other prior MIT distributions remain explicit;
- keep the committed dependency manifests/locks and this review record;
- preserve third-party license/copyright material for separately licensed or packaged third-party content.

For the production container image:

- keep `/app/LICENSE`;
- keep `/app/LICENSE-NOTICE.md`;
- record `org.opencontainers.image.licenses=AGPL-3.0-only`;
- preserve installed dependency metadata/license files supplied by package distributions;
- publish immutable source/build revision metadata with the image;
- do not represent third-party dependencies as AGPL-licensed GoreeCloud code.

For the Linux Debian client package:

- install the canonical repository `LICENSE` and `LICENSE-NOTICE.md` under `/usr/share/doc/goreecloud-notify/`;
- do not create duplicate source-of-truth copies of those legal files inside the client source tree.

Current Android APKs are source/CI acceptance artifacts rather than the final approved production-signed distribution. The final Android release/signing packaging contract must preserve the application license and applicable third-party notices without creating a conflicting duplicate licensing authority.

If a future dependency introduces a license with additional redistribution, attribution, notice, source-offer, or other obligations, the dependency review must be updated before that release is approved.

## Current-source licensing gate

The current-source relicensing gate is satisfied only when all of the following are true on one exact head:

- root `LICENSE` declares `SPDX-License-Identifier: AGPL-3.0-only`;
- `LICENSE-NOTICE.md` preserves the `v0.2.0` MIT grant and prior MIT distributions;
- README identifies current source as AGPL-3.0-only and prior `v0.2.0` as MIT;
- the production image carries AGPL-3.0-only OCI metadata and includes both licensing files;
- the Linux Debian package includes both canonical licensing files;
- strict dependency-license inventory passes;
- repository licensing regression coverage passes;
- all applicable backend/frontend/readiness/native-client validation remains green on the exact relicensing head.

Production deployment remains separately controlled by target recovery, monitoring/out-of-band alerting, private-publication/runtime, manual browser/OS acceptance, Android production-signing/device acceptance, controlled migration, and rollback gates.
