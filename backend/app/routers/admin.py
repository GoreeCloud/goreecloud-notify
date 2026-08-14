from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..datetime_utils import as_utc
from ..deps import get_db
from ..models import AccessToken, Channel, ServiceIdentity, Source, User
from ..schemas import (
    ChannelCreate,
    ChannelRead,
    ServiceIdentityCreate,
    ServiceIdentityRead,
    SourceCreate,
    SourceRead,
    TokenCreate,
    TokenCreated,
    UserCreate,
    UserRead,
)
from ..security import issue_token, require_admin, scopes_to_string, token_digest
from ..user_security import hash_password

router = APIRouter(tags=["administration"], dependencies=[Depends(require_admin)])


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: Annotated[Session, Depends(get_db)]) -> UserRead:
    user = User(
        username=payload.username.strip().lower(),
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="user already exists") from exc
    session.refresh(user)
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
    )


@router.post("/service-identities", response_model=ServiceIdentityRead, status_code=status.HTTP_201_CREATED)
def create_service_identity(
    payload: ServiceIdentityCreate,
    session: Annotated[Session, Depends(get_db)],
) -> ServiceIdentityRead:
    identity = ServiceIdentity(name=payload.name.strip(), description=payload.description)
    session.add(identity)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="service identity already exists") from exc
    session.refresh(identity)
    return ServiceIdentityRead(
        id=identity.id,
        name=identity.name,
        description=identity.description,
        enabled=identity.enabled,
    )


@router.post("/tokens", response_model=TokenCreated, status_code=status.HTTP_201_CREATED)
def create_token(payload: TokenCreate, session: Annotated[Session, Depends(get_db)]) -> TokenCreated:
    identity = session.get(ServiceIdentity, payload.service_identity_id)
    if identity is None or not identity.enabled:
        raise HTTPException(status_code=404, detail="service identity not found")

    raw_token = issue_token()
    record = AccessToken(
        service_identity_id=identity.id,
        name=payload.name.strip(),
        token_digest=token_digest(raw_token),
        scope=scopes_to_string(payload.scopes),
        expires_at=payload.expires_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return TokenCreated(
        id=record.id,
        name=record.name,
        token=raw_token,
        scopes=sorted(payload.scopes),
        expires_at=as_utc(record.expires_at) if record.expires_at is not None else None,
    )


@router.post("/tokens/{token_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(token_id: int, session: Annotated[Session, Depends(get_db)]) -> None:
    record = session.get(AccessToken, token_id)
    if record is None:
        raise HTTPException(status_code=404, detail="token not found")
    record.enabled = False
    session.commit()


@router.get("/sources", response_model=list[SourceRead])
def list_sources(session: Annotated[Session, Depends(get_db)]) -> list[SourceRead]:
    rows = session.scalars(select(Source).order_by(Source.slug)).all()
    return [
        SourceRead(
            id=row.id,
            service_identity_id=row.service_identity_id,
            slug=row.slug,
            name=row.name,
        )
        for row in rows
        if row.service_identity_id is not None
    ]


@router.post("/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, session: Annotated[Session, Depends(get_db)]) -> SourceRead:
    identity = session.get(ServiceIdentity, payload.service_identity_id)
    if identity is None or not identity.enabled:
        raise HTTPException(status_code=404, detail="service identity not found")
    source = Source(
        service_identity_id=identity.id,
        slug=payload.slug,
        name=payload.name.strip(),
    )
    session.add(source)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="source already exists") from exc
    session.refresh(source)
    return SourceRead(
        id=source.id,
        service_identity_id=identity.id,
        slug=source.slug,
        name=source.name,
    )


@router.get("/channels", response_model=list[ChannelRead])
def list_channels(session: Annotated[Session, Depends(get_db)]) -> list[ChannelRead]:
    rows = session.scalars(select(Channel).order_by(Channel.slug)).all()
    return [ChannelRead(id=row.id, slug=row.slug, name=row.name, description=row.description) for row in rows]


@router.post("/channels", response_model=ChannelRead, status_code=status.HTTP_201_CREATED)
def create_channel(payload: ChannelCreate, session: Annotated[Session, Depends(get_db)]) -> ChannelRead:
    channel = Channel(slug=payload.slug, name=payload.name.strip(), description=payload.description)
    session.add(channel)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="channel already exists") from exc
    session.refresh(channel)
    return ChannelRead(id=channel.id, slug=channel.slug, name=channel.name, description=channel.description)
