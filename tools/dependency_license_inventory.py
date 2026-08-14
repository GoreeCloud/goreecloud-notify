from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Iterable


_NAME_NORMALIZER = re.compile(r"[-_.]+")


@dataclass(frozen=True)
class DependencyRecord:
    ecosystem: str
    name: str
    version: str
    license: str
    source: str
    package_path: str | None = None
    development_only: bool = False
    optional: bool = False


def normalize_python_name(name: str) -> str:
    return _NAME_NORMALIZER.sub("-", name).lower()


def parse_constraints(path: Path) -> dict[str, tuple[str, str]]:
    constraints: dict[str, tuple[str, str]] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        if "==" not in line:
            raise ValueError(f"{path}:{line_number}: expected an exact 'name==version' constraint")
        name, version = (part.strip() for part in line.split("==", 1))
        if not name or not version:
            raise ValueError(f"{path}:{line_number}: invalid exact dependency constraint")
        normalized = normalize_python_name(name)
        if normalized in constraints:
            raise ValueError(f"{path}:{line_number}: duplicate dependency constraint for {name}")
        constraints[normalized] = (name, version)
    if not constraints:
        raise ValueError(f"{path}: no exact dependency constraints found")
    return constraints


def compact_metadata(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) <= 160:
        return compact
    return compact[:157] + "..."


def python_license(dist: metadata.Distribution) -> tuple[str, str]:
    license_expression = dist.metadata.get("License-Expression")
    if license_expression and license_expression.strip():
        return compact_metadata(license_expression), "installed package License-Expression"

    classifiers = [
        classifier.removeprefix("License :: ").strip()
        for classifier in (dist.metadata.get_all("Classifier") or [])
        if classifier.startswith("License :: ")
    ]
    if classifiers:
        return " | ".join(sorted(set(classifiers))), "installed package license classifier"

    license_value = dist.metadata.get("License")
    if license_value and license_value.strip() and license_value.strip().upper() != "UNKNOWN":
        return compact_metadata(license_value), "installed package License metadata"

    return "UNKNOWN", "installed package metadata"


def collect_python_records(constraints_path: Path) -> tuple[list[DependencyRecord], list[str]]:
    constraints = parse_constraints(constraints_path)
    records: list[DependencyRecord] = []
    errors: list[str] = []

    for _, (declared_name, expected_version) in sorted(constraints.items()):
        try:
            dist = metadata.distribution(declared_name)
        except metadata.PackageNotFoundError:
            errors.append(f"Python dependency is not installed: {declared_name}=={expected_version}")
            continue

        installed_name = dist.metadata.get("Name") or declared_name
        if dist.version != expected_version:
            errors.append(
                f"Python dependency version mismatch for {installed_name}: "
                f"constraints={expected_version}, installed={dist.version}"
            )
        license_value, source = python_license(dist)
        records.append(
            DependencyRecord(
                ecosystem="python",
                name=installed_name,
                version=dist.version,
                license=license_value,
                source=source,
            )
        )

    return sorted(records, key=lambda record: (record.name.lower(), record.version)), errors


def frontend_package_name(package_path: str) -> str:
    tail = package_path.rsplit("node_modules/", 1)[-1]
    if tail.startswith("@"):
        parts = tail.split("/")
        if len(parts) < 2:
            return tail
        return "/".join(parts[:2])
    return tail.split("/", 1)[0]


def collect_frontend_records(lock_path: Path) -> tuple[list[DependencyRecord], list[str]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("lockfileVersion") != 3:
        raise ValueError(f"{lock_path}: expected npm package-lock lockfileVersion 3")
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise ValueError(f"{lock_path}: missing packages object")

    records: list[DependencyRecord] = []
    errors: list[str] = []
    for package_path, package in sorted(packages.items()):
        if not package_path or "node_modules/" not in package_path:
            continue
        if not isinstance(package, dict):
            errors.append(f"Frontend lock entry is not an object: {package_path}")
            continue
        version = package.get("version")
        if not isinstance(version, str) or not version:
            errors.append(f"Frontend lock entry has no exact version: {package_path}")
            continue
        license_value = package.get("license")
        if not isinstance(license_value, str) or not license_value.strip():
            license_value = "UNKNOWN"
        else:
            license_value = compact_metadata(license_value)
        records.append(
            DependencyRecord(
                ecosystem="npm",
                name=frontend_package_name(package_path),
                version=version,
                license=license_value,
                source="package-lock.json license metadata",
                package_path=package_path,
                development_only=bool(package.get("dev", False)),
                optional=bool(package.get("optional", False)),
            )
        )

    if not records:
        errors.append("Frontend package-lock contains no node_modules dependency entries")
    return records, errors


def escape_markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def markdown_table(records: Iterable[DependencyRecord]) -> list[str]:
    lines = [
        "| Package | Version | License metadata | Scope |",
        "|---|---|---|---|",
    ]
    for record in records:
        scope = ["dev" if record.development_only else "runtime/lock"]
        if record.optional:
            scope.append("optional")
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_markdown(record.name),
                    escape_markdown(record.version),
                    escape_markdown(record.license),
                    escape_markdown(", ".join(scope)),
                ]
            )
            + " |"
        )
    return lines


def render_markdown(
    python_records: list[DependencyRecord],
    frontend_records: list[DependencyRecord],
    errors: list[str],
) -> str:
    unknown = [record for record in [*python_records, *frontend_records] if record.license == "UNKNOWN"]
    lines = [
        "## GoreeCloud Notify dependency license inventory",
        "",
        "This inventory is generated from the exact Python constraint closure, installed Python package metadata, and the committed npm lockfile. It is evidence for human license review; it is not legal approval or an automatic compatibility decision.",
        "",
        f"- Python dependencies inventoried: **{len(python_records)}**",
        f"- Frontend lock entries inventoried: **{len(frontend_records)}**",
        f"- Dependencies with unknown license metadata: **{len(unknown)}**",
        f"- Structural/version validation errors: **{len(errors)}**",
        "",
        "### Python",
        "",
        *markdown_table(python_records),
        "",
        "### Frontend/npm",
        "",
        *markdown_table(frontend_records),
    ]
    if unknown:
        lines.extend(
            [
                "",
                "### Manual review required: missing license metadata",
                "",
                *[f"- `{record.ecosystem}:{record.name}@{record.version}`" for record in unknown],
            ]
        )
    if errors:
        lines.extend(["", "### Validation errors", "", *[f"- {error}" for error in errors]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory exact GoreeCloud Notify dependency versions and declared license metadata."
    )
    parser.add_argument("--constraints", type=Path, default=Path("backend/constraints.txt"))
    parser.add_argument("--package-lock", type=Path, default=Path("frontend/package-lock.json"))
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when a dependency cannot be resolved, versions drift, or license metadata is unknown.",
    )
    args = parser.parse_args()

    python_records, python_errors = collect_python_records(args.constraints)
    frontend_records, frontend_errors = collect_frontend_records(args.package_lock)
    errors = [*python_errors, *frontend_errors]
    unknown = [record for record in [*python_records, *frontend_records] if record.license == "UNKNOWN"]

    if args.format == "json":
        output = {
            "python": [asdict(record) for record in python_records],
            "frontend": [asdict(record) for record in frontend_records],
            "unknown_license_metadata": [asdict(record) for record in unknown],
            "errors": errors,
        }
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_markdown(python_records, frontend_records, errors))

    if errors:
        return 1
    if args.strict and unknown:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
