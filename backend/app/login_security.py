from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .datetime_utils import as_utc
from .models import LoginRateBucket, LoginSecurityEvent


@dataclass(frozen=True, slots=True)
class LoginContext:
    client_signal: str
    client_digest: str
    account_digest: str
    source_key_digest: str
    source_account_key_digest: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _trusted_networks():
    return tuple(ip_network(cidr, strict=False) for cidr in settings.trusted_proxy_cidrs)


def _trusted(address) -> bool:
    return any(address in network for network in _trusted_networks())


def resolve_client_signal(request: Request) -> str:
    peer_host = request.client.host if request.client is not None else "unknown"
    try:
        peer = ip_address(peer_host)
    except ValueError:
        return peer_host

    if not _trusted(peer):
        return peer.compressed

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer.compressed

    chain = []
    for item in forwarded.split(","):
        try:
            chain.append(ip_address(item.strip()))
        except ValueError:
            return peer.compressed
    chain.append(peer)

    for candidate in reversed(chain):
        if not _trusted(candidate):
            return candidate.compressed
    return chain[0].compressed


def build_login_context(request: Request, username: str) -> LoginContext:
    client_signal = resolve_client_signal(request)
    normalized_account = username.strip().lower()
    client_digest = _digest(f"client:{client_signal}")
    account_digest = _digest(f"account:{normalized_account}")
    return LoginContext(
        client_signal=client_signal,
        client_digest=client_digest,
        account_digest=account_digest,
        source_key_digest=_digest(f"source:{client_digest}"),
        source_account_key_digest=_digest(
            f"source-account:{client_digest}:{account_digest}"
        ),
    )


def _cleanup(session: Session, now: datetime) -> None:
    session.execute(
        delete(LoginRateBucket).where(
            LoginRateBucket.updated_at
            < now - timedelta(hours=settings.login_rate_state_ttl_hours)
        )
    )
    session.execute(
        delete(LoginSecurityEvent).where(
            LoginSecurityEvent.created_at
            < now - timedelta(days=settings.login_security_event_retention_days)
        )
    )


def _bucket(session: Session, key_digest: str, scope: str, now: datetime) -> LoginRateBucket:
    record = session.scalar(
        select(LoginRateBucket).where(LoginRateBucket.key_digest == key_digest)
    )
    if record is not None:
        return record

    candidate = LoginRateBucket(
        key_digest=key_digest,
        scope=scope,
        window_started_at=now,
        failure_count=0,
        blocked_until=None,
        updated_at=now,
    )
    try:
        with session.begin_nested():
            session.add(candidate)
            session.flush()
        return candidate
    except IntegrityError:
        record = session.scalar(
            select(LoginRateBucket).where(LoginRateBucket.key_digest == key_digest)
        )
        if record is None:
            raise
        return record


def _reset_if_elapsed(record: LoginRateBucket, now: datetime) -> None:
    blocked_until = as_utc(record.blocked_until) if record.blocked_until is not None else None
    window_started = as_utc(record.window_started_at)
    if blocked_until is not None and blocked_until <= now:
        record.window_started_at = now
        record.failure_count = 0
        record.blocked_until = None
    elif window_started + timedelta(minutes=settings.login_rate_window_minutes) <= now:
        record.window_started_at = now
        record.failure_count = 0
        record.blocked_until = None
    record.updated_at = now


def _retry_after_seconds(record: LoginRateBucket, now: datetime) -> int:
    if record.blocked_until is None:
        return 0
    seconds = (as_utc(record.blocked_until) - now).total_seconds()
    return max(0, math.ceil(seconds))


def _event(session: Session, context: LoginContext, outcome: str, now: datetime) -> None:
    session.add(
        LoginSecurityEvent(
            outcome=outcome,
            client_digest=context.client_digest,
            account_digest=context.account_digest,
            created_at=now,
        )
    )


def check_login_rate_limit(
    session: Session,
    context: LoginContext,
    *,
    now: datetime | None = None,
) -> int:
    now = now or utc_now()
    retries: list[int] = []
    for key_digest in (
        context.source_key_digest,
        context.source_account_key_digest,
    ):
        record = session.scalar(
            select(LoginRateBucket).where(LoginRateBucket.key_digest == key_digest)
        )
        if record is not None:
            retries.append(_retry_after_seconds(record, now))
    return max(retries, default=0)


def record_rate_limited(
    session: Session,
    context: LoginContext,
    *,
    now: datetime | None = None,
) -> None:
    now = now or utc_now()
    _cleanup(session, now)
    _event(session, context, "rate_limited", now)
    session.commit()


def record_login_failure(
    session: Session,
    context: LoginContext,
    *,
    now: datetime | None = None,
) -> int:
    now = now or utc_now()
    _cleanup(session, now)
    retry_after = 0
    for key_digest, scope, limit in (
        (context.source_key_digest, "source", settings.login_rate_source_attempts),
        (
            context.source_account_key_digest,
            "source_account",
            settings.login_rate_account_attempts,
        ),
    ):
        record = _bucket(session, key_digest, scope, now)
        _reset_if_elapsed(record, now)
        record.failure_count += 1
        record.updated_at = now
        if record.failure_count >= limit:
            record.blocked_until = now + timedelta(
                minutes=settings.login_rate_cooldown_minutes
            )
        retry_after = max(retry_after, _retry_after_seconds(record, now))

    _event(session, context, "rate_limited" if retry_after else "failure", now)
    session.commit()
    return retry_after


def record_login_success(
    session: Session,
    context: LoginContext,
    *,
    now: datetime | None = None,
) -> None:
    now = now or utc_now()
    _cleanup(session, now)
    record = session.scalar(
        select(LoginRateBucket).where(
            LoginRateBucket.key_digest == context.source_account_key_digest
        )
    )
    if record is not None:
        record.window_started_at = now
        record.failure_count = 0
        record.blocked_until = None
        record.updated_at = now
    _event(session, context, "success", now)
    session.commit()
