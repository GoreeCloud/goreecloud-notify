#!/usr/bin/env python3
"""Read-only target evidence collector for GoreeCloud Notify production readiness."""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import stat
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CSP = "; ".join((
    "default-src 'self'", "base-uri 'none'", "object-src 'none'",
    "frame-ancestors 'none'", "frame-src 'none'", "form-action 'self'",
    "script-src 'self'", "style-src 'self'", "img-src 'self' data:",
    "font-src 'self'", "connect-src 'self'", "media-src 'none'",
    "worker-src 'none'", "manifest-src 'self'",
))
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
NETBIRD = ipaddress.ip_network("100.64.0.0/10")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
LOG_MARKERS = {
    "authorization_header": re.compile(r"\bauthorization\s*:", re.I),
    "bearer_token": re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I),
    "cookie_header": re.compile(r"\b(?:set-)?cookie\s*:", re.I),
    "admin_token_assignment": re.compile(r"\bGOREECLOUD_NOTIFY_ADMIN_TOKEN\s*=", re.I),
    "password_assignment": re.compile(r"\bpassword\s*=", re.I),
}


def command(*parts: str) -> str:
    result = subprocess.run(parts, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def dinspect(container: str, template: str) -> str:
    return command("docker", "inspect", "--format", template, container)


def decoded(value: str, default):
    return default if not value or value == "<no value>" else json.loads(value)


def add(checks: list[dict[str, str]], name: str, ok: bool, good: str, bad: str) -> None:
    checks.append({"name": name, "status": "pass" if ok else "fail", "detail": good if ok else bad})


def browser_headers(headers) -> None:
    expected = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": CSP,
        "X-Frame-Options": "DENY",
        "Permissions-Policy": PERMISSIONS_POLICY,
    }
    for name, value in expected.items():
        if headers.get(name) != value:
            raise AssertionError(f"unexpected {name}")


def private_headers(headers) -> None:
    if headers.get("Cache-Control") != "no-store" or headers.get("Pragma") != "no-cache":
        raise AssertionError("private cache policy is missing")
    browser_headers(headers)


def request(base: str, path: str, *, method: str = "GET", headers=None, expected: int = 200):
    req = urllib.request.Request(
        urllib.parse.urljoin(base.rstrip("/") + "/", path.lstrip("/")),
        headers={"User-Agent": "goreecloud-notify-target-preflight/1", **(headers or {})},
        method=method,
    )
    try:
        response = urllib.request.urlopen(req, timeout=8)
    except urllib.error.HTTPError as exc:
        if exc.code != expected:
            raise AssertionError(f"{method} {path} returned {exc.code}, expected {expected}") from exc
        return exc.read(), exc.headers
    with response:
        if response.status != expected:
            raise AssertionError(f"{method} {path} returned {response.status}, expected {expected}")
        return response.read(), response.headers


def host_checks(args, checks: list[dict[str, str]]) -> None:
    try:
        user = dinspect(args.container, "{{.Config.User}}")
        add(checks, "container_user", user == "10001:10001", "runtime user is 10001:10001", f"runtime user is {user!r}")
        ro = dinspect(args.container, "{{.HostConfig.ReadonlyRootfs}}").lower()
        add(checks, "read_only_rootfs", ro == "true", "root filesystem is read-only", "root filesystem is writable")
        pids = int(dinspect(args.container, "{{.HostConfig.PidsLimit}}"))
        add(checks, "pids_limit", pids == 256, "PID limit is 256", f"PID limit is {pids}")
        sec = decoded(dinspect(args.container, "{{json .HostConfig.SecurityOpt}}"), [])
        add(checks, "no_new_privileges", any(str(x).startswith("no-new-privileges") for x in sec), "no-new-privileges is enabled", "no-new-privileges is absent")
        caps = decoded(dinspect(args.container, "{{json .HostConfig.CapDrop}}"), [])
        add(checks, "capabilities", "ALL" in caps, "all Linux capabilities are dropped", f"capability drop set is {caps!r}")
        ports = decoded(dinspect(args.container, "{{json .HostConfig.PortBindings}}"), {})
        add(checks, "host_ports", not ports, "no host ports are published", f"host port bindings are present: {sorted(ports)}")
        mode = dinspect(args.container, "{{.HostConfig.NetworkMode}}")
        networks = sorted(decoded(dinspect(args.container, "{{json .NetworkSettings.Networks}}"), {}))
        add(checks, "docker_networks", mode == "proxy" and networks == ["proxy"], "container is attached only to proxy", f"network mode={mode!r}, attached={networks!r}")
        tmpfs = decoded(dinspect(args.container, "{{json .HostConfig.Tmpfs}}"), {})
        tmp = str(tmpfs.get("/tmp", ""))
        add(checks, "tmpfs", "/tmp" in tmpfs and "noexec" in tmp and "nosuid" in tmp, "/tmp uses noexec,nosuid tmpfs", f"unexpected /tmp tmpfs: {tmpfs!r}")
        health = dinspect(args.container, "{{.State.Health.Status}}")
        add(checks, "container_health", health == "healthy", "container is healthy", f"container health is {health!r}")
        mounts = decoded(dinspect(args.container, "{{json .Mounts}}"), [])
        data = [m for m in mounts if m.get("Destination") == "/data" and m.get("Type") == "bind"]
        mount_ok = len(data) == 1 and Path(data[0].get("Source", "")).resolve() == args.data_dir
        add(checks, "data_mount", mount_ok, f"/data is bound from {args.data_dir}", "/data bind does not match approved data directory")
        image_ref = dinspect(args.container, "{{.Config.Image}}")
        image_id = dinspect(args.container, "{{.Image}}")
        checks += [
            {"name": "container_image_ref", "status": "pass", "detail": image_ref},
            {"name": "container_image_id", "status": "pass", "detail": image_id},
        ]
        revision = command("docker", "image", "inspect", "--format", '{{ index .Config.Labels "org.opencontainers.image.revision" }}', image_id)
        add(checks, "image_revision", revision == args.expected_revision, f"OCI image revision matches {args.expected_revision}", f"OCI image revision is {revision!r}")
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        add(checks, "docker_runtime_inspection", False, "", f"runtime inspection failed: {type(exc).__name__}")

    for path, kind in ((args.env_file, "env"), (args.data_dir, "data"), (args.data_dir / "goreecloud_notify.db", "database")):
        try:
            info = path.stat()
            mode_bits, owner = stat.S_IMODE(info.st_mode), f"{info.st_uid}:{info.st_gid}"
            if kind == "env":
                add(checks, "env_file_mode", mode_bits in {0o600, 0o640}, f"protected environment file mode is {mode_bits:04o}", f"protected environment file mode is {mode_bits:04o}; expected 0600 or 0640")
                checks.append({"name": "env_file_owner", "status": "pass", "detail": owner})
            else:
                add(checks, f"{kind}_owner", owner == "10001:10001", f"{kind} owner/group is 10001:10001", f"{kind} owner/group is {owner}")
                perms_ok = (mode_bits & 0o007) == 0 and bool(mode_bits & 0o200) and (kind != "data" or bool(mode_bits & 0o100))
                add(checks, f"{kind}_mode", perms_ok, f"{kind} mode {mode_bits:04o} is restrictive", f"{kind} mode {mode_bits:04o} is too broad or not owner-writable")
        except OSError as exc:
            add(checks, f"{kind}_path", False, "", f"cannot stat {kind} path: {exc.strerror}")

    try:
        log_text = command("docker", "logs", "--tail", str(args.log_lines), args.container)
        found = {name: len(rx.findall(log_text)) for name, rx in LOG_MARKERS.items() if rx.search(log_text)}
        add(checks, "runtime_log_scan", not found, f"last {args.log_lines} log lines contain no protected-value marker patterns", f"protected-value marker counts detected without printing matched content: {found}")
    except (OSError, subprocess.CalledProcessError):
        add(checks, "runtime_log_scan", False, "", "could not read bounded container logs")


def network_checks(args, checks: list[dict[str, str]]) -> None:
    parsed = urllib.parse.urlparse(args.base_url)
    add(checks, "https_scheme", parsed.scheme == "https", "target origin uses HTTPS", "target origin is not HTTPS")
    if parsed.scheme != "https" or not parsed.hostname:
        return
    try:
        addresses = sorted({x[4][0] for x in socket.getaddrinfo(parsed.hostname, 443, socket.AF_INET, socket.SOCK_STREAM)})
        private = bool(addresses) and all(ipaddress.ip_address(x) in NETBIRD for x in addresses)
        add(checks, "private_dns", private, f"{parsed.hostname} resolves only inside NetBird IPv4 space: {', '.join(addresses)}", f"{parsed.hostname} resolved outside NetBird IPv4 space: {', '.join(addresses) or 'no IPv4 answer'}")
    except (OSError, ValueError) as exc:
        add(checks, "private_dns", False, "", f"DNS resolution failed: {type(exc).__name__}")

    try:
        body, headers = request(args.base_url, "/healthz"); private_headers(headers)
        health = json.loads(body)
        if health.get("status") != "ok" or "build_revision" in health: raise AssertionError("unexpected health payload")
        add(checks, "https_health", True, "verified-TLS /healthz and private headers passed", "")

        body, headers = request(args.base_url, "/api/v1/meta"); private_headers(headers)
        meta = json.loads(body)
        if meta.get("production") is not True or meta.get("build_revision") != args.expected_revision: raise AssertionError("production metadata revision mismatch")
        add(checks, "https_meta", True, "production metadata reports exact expected revision", "")

        for path, name in (("/api/v1/me", "unauthenticated_session"), ("/api/v1/inbox/stream", "unauthenticated_sse")):
            _, headers = request(args.base_url, path, expected=401); private_headers(headers)
            add(checks, name, True, f"unauthenticated {path} is denied with private headers", "")

        index, headers = request(args.base_url, "/"); private_headers(headers)
        match = re.search(r'(?:src|href)="(/assets/[^"]+)"', index.decode())
        if not match: raise AssertionError("production index has no built asset")
        _, headers = request(args.base_url, match.group(1)); browser_headers(headers)
        cache = headers.get("Cache-Control", "")
        if "immutable" not in cache or "max-age=31536000" not in cache or headers.get("Pragma") is not None: raise AssertionError("asset cache policy mismatch")
        add(checks, "frontend_cache_policy", True, "HTML is no-store and built assets are immutable", "")

        _, headers = request(args.base_url, "/api/v1/meta", method="OPTIONS", headers={"Origin": args.base_url.rstrip("/"), "Access-Control-Request-Method": "GET"})
        private_headers(headers)
        if headers.get("Access-Control-Allow-Origin") != args.base_url.rstrip("/") or headers.get("Access-Control-Allow-Credentials") != "true": raise AssertionError("CORS mismatch")
        add(checks, "same_origin_cors", True, "same-origin credentialed CORS preflight passed", "")
    except (AssertionError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, UnicodeDecodeError) as exc:
        add(checks, "https_private_path", False, "", f"HTTPS validation failed: {exc}")


def self_test() -> None:
    checks: list[dict[str, str]] = []
    add(checks, "yes", True, "ok", "bad"); add(checks, "no", False, "ok", "expected")
    assert REVISION_RE.fullmatch("a" * 40) and not REVISION_RE.fullmatch("development")
    assert ipaddress.ip_address("100.71.27.119") in NETBIRD
    assert ipaddress.ip_address("135.148.45.22") not in NETBIRD
    private_headers({"Cache-Control":"no-store","Pragma":"no-cache","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer","Content-Security-Policy":CSP,"X-Frame-Options":"DENY","Permissions-Policy":PERMISSIONS_POLICY})
    assert not any(rx.search("INFO startup complete") for rx in LOG_MARKERS.values())
    assert LOG_MARKERS["bearer_token"].search("Authorization: Bearer synthetic-secret-value")
    print("target preflight self-test passed")


def arguments():
    p = argparse.ArgumentParser(description="Read-only GoreeCloud Notify target production preflight")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--scope", choices=("host", "network", "all"), default="all")
    p.add_argument("--base-url"); p.add_argument("--expected-revision")
    p.add_argument("--container", default="goreecloud-notify")
    p.add_argument("--data-dir", type=Path); p.add_argument("--env-file", type=Path)
    p.add_argument("--log-lines", type=int, default=500)
    p.add_argument("--output", type=Path, default=Path("goreecloud-notify-target-preflight.json"))
    args = p.parse_args()
    if args.self_test: return args
    required = {"--expected-revision": args.expected_revision}
    if args.scope in {"network", "all"}: required["--base-url"] = args.base_url
    if args.scope in {"host", "all"}: required.update({"--data-dir": args.data_dir, "--env-file": args.env_file})
    missing = [k for k, v in required.items() if v is None or v == ""]
    if missing: p.error("missing required arguments: " + ", ".join(missing))
    if not REVISION_RE.fullmatch(args.expected_revision): p.error("--expected-revision must be an exact 40-character lowercase Git SHA")
    if not 1 <= args.log_lines <= 5000: p.error("--log-lines must be between 1 and 5000")
    if args.data_dir is not None: args.data_dir = args.data_dir.resolve()
    if args.env_file is not None: args.env_file = args.env_file.resolve()
    args.output = args.output.resolve()
    return args


def main() -> int:
    args = arguments()
    if args.self_test: self_test(); return 0
    checks: list[dict[str, str]] = []
    if args.scope in {"host", "all"}: host_checks(args, checks)
    if args.scope in {"network", "all"}: network_checks(args, checks)
    ok = bool(checks) and all(x["status"] == "pass" for x in checks)
    report = {
        "schema": "goreecloud-notify-target-preflight-v1",
        "generated_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "scope": args.scope, "base_url": args.base_url,
        "expected_revision": args.expected_revision,
        "container": args.container if args.scope in {"host", "all"} else None,
        "data_dir": str(args.data_dir) if args.data_dir else None,
        "env_file": str(args.env_file) if args.env_file else None,
        "result": "pass" if ok else "fail", "checks": checks,
        "limitations": [
            "No authenticated browser/session acceptance is proven.",
            "Approved-versus-denied NetBird access from two real source locations is not proven.",
            "Long-lived authenticated SSE, revocation/expiry, and prolonged network interruption recovery are not proven.",
            "Backup/restore, Uptime Kuma/out-of-band alerting, producer migration, and ntfy rollback are not proven.",
            "The bounded log marker scan is a regression aid, not exhaustive secret-leak proof.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in checks: print(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
    print(f"Evidence written to {args.output}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
