from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MANDATORY_ROOT_CONTROLS = [
    "README.md",
    "SPECIFICATIONS.md",
    "FEATURES.md",
    "FEATURE-ROADMAP.md",
    "BENEFITS.md",
    "COMPETITIVE-OBJECTIVES.md",
    "BRANDING.md",
    "USER-MANUAL.md",
    "PRIVACY POLICY.md",
    "NOTES.md",
    "SECURITY.md",
    ".gitignore",
    ".editorconfig",
    "goreecloud.platform.yaml",
]


def test_mandatory_repository_controls_exist() -> None:
    missing = [name for name in MANDATORY_ROOT_CONTROLS if not (ROOT / name).is_file()]
    assert missing == []


def test_repository_controls_keep_release_candidate_boundary() -> None:
    specs = (ROOT / "SPECIFICATIONS.md").read_text(encoding="utf-8")
    features = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
    notes = (ROOT / "NOTES.md").read_text(encoding="utf-8")
    assert "release candidate" in specs.lower()
    assert "not automatically production-accepted" in features.lower()
    assert "production acceptance remains false" in notes.lower()
