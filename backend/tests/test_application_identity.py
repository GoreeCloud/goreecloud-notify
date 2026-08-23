import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
ICON_REL = "frontend/public/brand/goreecloud-notify-icon.svg"
ICON_URL = "/brand/goreecloud-notify-icon.svg"


def test_canonical_icon_is_local_scalable_and_script_free() -> None:
    icon_path = ROOT / ICON_REL
    assert icon_path.is_file()

    root = ET.parse(icon_path).getroot()
    assert root.tag.rsplit("}", 1)[-1] == "svg"
    assert root.attrib["viewBox"] == "0 0 512 512"

    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        assert local_name not in {"script", "image", "foreignObject"}
        for value in element.attrib.values():
            lowered = value.lower()
            assert "http://" not in lowered
            assert "https://" not in lowered
            assert "data:" not in lowered


def test_web_metadata_and_product_marks_use_canonical_icon() -> None:
    index_html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert f'<link rel="icon" type="image/svg+xml" href="{ICON_URL}" />' in index_html
    assert '<link rel="manifest" href="/manifest.webmanifest" />' in index_html
    assert '<meta name="application-name" content="GoreeCloud Notify" />' in index_html

    refinement_css = (ROOT / "frontend/src/refinement.css").read_text(encoding="utf-8")
    assert f"url('{ICON_URL}')" in refinement_css

    manifest = json.loads((ROOT / "frontend/public/manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["id"] == "/"
    assert manifest["name"] == "GoreeCloud Notify"
    assert manifest["short_name"] == "Notify"
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["icons"] == [
        {
            "src": ICON_URL,
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable",
        }
    ]


def test_packaging_contract_reuses_same_canonical_identity() -> None:
    contract = json.loads((ROOT / "packaging/application-identity.json").read_text(encoding="utf-8"))

    assert contract["schema_version"] == 2
    assert contract["product"] == "GoreeCloud Notify"
    assert contract["canonical_icon"] == ICON_REL
    assert contract["web"] == {
        "favicon": ICON_REL,
        "manifest": "frontend/public/manifest.webmanifest",
    }
    assert contract["linux"] == {
        "target": "deb",
        "package_name": "goreecloud-notify",
        "artifact_pattern": "goreecloud-notify_<version>_amd64.deb",
        "icon_source": ICON_REL,
    }
    assert contract["android"] == {
        "target": "APK",
        "application_id": "com.goreecloud.goreecloud_notify_client",
        "acceptance_artifact": "goreecloud-notify-android-acceptance.apk",
        "icon_source": ICON_REL,
        "production_signing": "external-protected-material-required",
    }
