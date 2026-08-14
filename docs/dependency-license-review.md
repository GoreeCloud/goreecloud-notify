# GoreeCloud Notify dependency license review

## Purpose

I use this record to define how I collect dependency-license evidence for GoreeCloud Notify before I approve a stable open-source release.

GoreeCloud Notify is original GoreeCloud-owned software, but it depends on third-party Python and npm packages. Selecting the GoreeCloud Notify application license does not remove the need to understand the licenses and redistribution obligations of those dependencies.

This record supports GitHub issue #54. It does not select a GoreeCloud Notify license and does not constitute legal approval.

## Automated evidence

The repository contains `tools/dependency_license_inventory.py`.

The tool:

- reads the complete exact Python dependency closure from `backend/constraints.txt`;
- resolves each pinned Python package from the installed CI environment;
- verifies that the installed Python version matches the exact constraint;
- records `License-Expression`, license classifiers, or other installed package license metadata in that preference order;
- reads every npm dependency entry from the committed `frontend/package-lock.json` lockfile;
- records the exact npm package version and lockfile license metadata;
- distinguishes development-only and optional npm entries;
- reports unknown license metadata explicitly rather than guessing;
- can emit Markdown or JSON;
- exits non-zero in strict mode when dependency resolution/version validation fails or license metadata is unknown.

CI runs the tool after the constrained backend environment is installed and appends the generated Markdown inventory to the GitHub Actions job summary.

## Interpretation boundary

The automated inventory is evidence, not a license-compatibility decision.

Before issue #54 can be closed, I must still review the collected metadata and any authoritative upstream license texts that are necessary to determine:

- whether each dependency can be redistributed under the planned GoreeCloud Notify distribution model;
- whether attribution, notice, source-offer, copyleft, network-use, or other obligations apply;
- whether application, development, optional, and transitive dependencies require different treatment;
- whether any dependency metadata is ambiguous or inconsistent with its authoritative upstream license;
- whether a `NOTICE`, third-party notices file, source offer, or other release artifact is required;
- whether the selected GoreeCloud Notify license is compatible with the dependency set and intended self-hosted/network-service use.

If automated metadata conflicts with authoritative upstream licensing information, the authoritative license text and verified upstream project record take precedence and the discrepancy must be documented.

## Stability boundary

This dependency-license evidence work does not authorize:

- selection of the GoreeCloud Notify license;
- public release;
- production deployment;
- ntfy cutover;
- producer or consumer migration;
- Caddy, DNS, NetBird, firewall, backup, monitoring, or other production changes.

The stable-release license gate remains open until the license choice and dependency obligations are explicitly reviewed, approved, documented, and integrated.
