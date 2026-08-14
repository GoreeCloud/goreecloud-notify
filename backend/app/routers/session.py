from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from ..schemas import SessionCreate, UserRead
from ..user_security import (
    UserPrincipal,
    authenticate_user,
    create_web_session,
    require_user_session,
    revoke_web_session,
)

router = APIRouter(tags=["user sessions"])


def _user_read(principal: UserPrincipal) -> UserRead:
    return UserRead(
        id=principal.user_id,
        username=principal.username,
        display_name=principal.display_name,
        is_active=True,
    )


@router.post("/session", response_model=UserRead)
def login(
    payload: SessionCreate,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> UserRead:
    user = authenticate_user(session, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    _, raw_token = create_web_session(session, user)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_lifetime_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: Annotated[Session, Depends(get_db)],
    raw_token: Annotated[
        str | None, Cookie(alias=settings.session_cookie_name)
    ] = None,
) -> None:
    revoke_web_session(session, raw_token)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
    )


@router.get("/me", response_model=UserRead)
def me(
    principal: Annotated[UserPrincipal, Depends(require_user_session)],
) -> UserRead:
    return _user_read(principal)
