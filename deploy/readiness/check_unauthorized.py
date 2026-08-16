from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://notify.goreecloud.com"
CA_CERT = Path("/readiness/root.crt")


def main() -> None:
    if not CA_CERT.is_file():
        raise RuntimeError("Caddy readiness CA was not provided")

    context = ssl.create_default_context(cafile=str(CA_CERT))
    request = urllib.request.Request(f"{BASE_URL}/healthz")
    try:
        urllib.request.urlopen(request, context=context, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code != 403:
            raise AssertionError(f"unauthorized source returned {exc.code}, expected 403") from exc
    else:
        raise AssertionError("unauthorized source unexpectedly reached GoreeCloud Notify")

    print("unauthorized-source readiness check passed (403)")


if __name__ == "__main__":
    main()
