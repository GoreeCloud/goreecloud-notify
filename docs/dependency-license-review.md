# GoreeCloud Notify dependency license review

## Decision

GoreeCloud Notify is licensed under the **MIT License** beginning with the 0.2.0 release line.

The choice is intentionally simple and permissive. It satisfies the GoreeCloud requirement for a recognized open-source license, permits independent inspection/use/modification/redistribution, and does not add an additional network-source-offer feature requirement to the private web application.

The canonical applied license is stored at the repository root in `LICENSE`. The production image also copies that file into `/app/LICENSE` and records `org.opencontainers.image.licenses=MIT`.

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

CI runs the strict inventory after the constrained backend environment is installed. A green strict inventory is required for the release line.

## Review conclusion

The current dependency inventory is suitable for the MIT-licensed GoreeCloud Notify distribution model.

Runtime application dependencies are consumed as separately maintained third-party packages and retain their own licenses. The current Python runtime closure is based on commonly permissive MIT/BSD-style components used by FastAPI, SQLAlchemy, Uvicorn, Alembic, Argon2, Pydantic/Starlette, and their support packages. The browser runtime is React/ReactDOM. Development/browser tooling is not part of the production runtime image; this includes Playwright/Axe tooling, whose independent licensing remains preserved by the dependency lock and package metadata.

The strict inventory previously completed without unknown license metadata or dependency-version drift. The release CI must continue to pass that same check after license integration.

No third-party package is relicensed as GoreeCloud-owned code. The root MIT license applies to original GoreeCloud Notify source; third-party dependencies remain governed by their respective upstream licenses.

## Distribution boundary

For source distribution:

- keep the root `LICENSE` file;
- keep the committed dependency manifests/locks and this review record;
- do not remove third-party license/copyright material from vendored or packaged third-party content if such content is introduced later.

For the production container image:

- keep `/app/LICENSE`;
- preserve installed dependency metadata/license files supplied by the package distributions;
- publish immutable source/build revision metadata with the image;
- do not represent third-party dependencies as MIT-licensed GoreeCloud code.

If a future dependency introduces a license with additional redistribution, attribution, notice, source-offer, or other obligations, the dependency review must be updated before that release is approved.

## Release gate result

The source-level licensing gate is considered satisfied when all of the following are true on one exact head:

- root `LICENSE` contains the applied MIT license;
- README identifies MIT consistently;
- production image carries license/version/source metadata and includes the license file;
- strict dependency-license inventory passes;
- backend/frontend/readiness validation remains green;
- repository license detection reports MIT after integration to the release/main branch.

Production deployment remains separately controlled by the target recovery, monitoring/out-of-band alerting, private-publication/runtime, manual browser/OS acceptance, and migration gates.
