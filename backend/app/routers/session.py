from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from ..login_security import (
    build_login_context,
    check_login_rate_limit,
    record_login_failure,
    record_login_success,
    record_rate_limited,
)
from ..schemas import CsrfTokenRead, SessionCreate, UserRead
from ..user_security import (
    CSRF_HEADER,
    UserPrincipal,
    authenticate_user,
    create_web_session,
    csrf_token_for_principal,
    require_csrf_user_session,
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
        is_admin=principal.is_admin,
    )


def _rate_limited(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="login temporarily unavailable",
        headers={"Retry-After": str(max(1, retry_after))},
    )


@router.post("/session", response_model=UserRead)
def login(
    payload: SessionCreate,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> UserRead:
    context = build_login_context(request, payload.username)
    retry_after = check_login_rate_limit(session, context)
    if retry_after:
        record_rate_limited(session, context)
        raise _rate_limited(retry_after)

    user = authenticate_user(session, payload.username, payload.password)
    if user is None:
        retry_after = record_login_failure(session, context)
        if retry_after:
            raise _rate_limited(retry_after)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    record_login_success(session, context)
    record, raw_token = create_web_session(session, user)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_lifetime_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    response.headers[CSRF_HEADER] = record.csrf_token
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    _principal: Annotated[UserPrincipal, Depends(require_csrf_user_session)],
    session: Annotated[Session, Depends(get_db)],
    raw_token: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
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


@router.get("/csrf", response_model=CsrfTokenRead)
def csrf_token(
    principal: Annotated[UserPrincipal, Depends(require_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> CsrfTokenRead:
    return CsrfTokenRead(csrf_token=csrf_token_for_principal(session, principal))
