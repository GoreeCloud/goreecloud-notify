from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Channel, Subscription
from ..schemas import SubscriptionRead
from ..user_security import UserPrincipal, require_csrf_user_session, require_user_session

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def subscription_read(channel: Channel, subscription: Subscription | None) -> SubscriptionRead:
    return SubscriptionRead(
        channel_id=channel.id,
        channel=channel.slug,
        name=channel.name,
        description=channel.description,
        subscribed=bool(subscription is not None and subscription.enabled),
    )


def resolve_channel(session: Session, channel_slug: str) -> Channel:
    channel = session.scalar(select(Channel).where(Channel.slug == channel_slug))
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="channel not found")
    return channel


def owned_subscription(session: Session, user_id: int, channel_id: int) -> Subscription | None:
    return session.scalar(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.channel_id == channel_id,
        )
    )


@router.get("", response_model=list[SubscriptionRead])
def list_subscriptions(
    principal: Annotated[UserPrincipal, Depends(require_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> list[SubscriptionRead]:
    channels = session.scalars(select(Channel).order_by(Channel.slug)).all()
    subscriptions = session.scalars(
        select(Subscription).where(Subscription.user_id == principal.user_id)
    ).all()
    subscriptions_by_channel = {subscription.channel_id: subscription for subscription in subscriptions}
    return [
        subscription_read(channel, subscriptions_by_channel.get(channel.id))
        for channel in channels
    ]


@router.put("/{channel_slug}", response_model=SubscriptionRead)
def subscribe(
    channel_slug: str,
    principal: Annotated[UserPrincipal, Depends(require_csrf_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> SubscriptionRead:
    channel = resolve_channel(session, channel_slug)
    subscription = owned_subscription(session, principal.user_id, channel.id)
    if subscription is None:
        subscription = Subscription(
            user_id=principal.user_id,
            channel_id=channel.id,
            enabled=True,
        )
        session.add(subscription)
    elif not subscription.enabled:
        subscription.enabled = True
    session.commit()
    return subscription_read(channel, subscription)


@router.delete("/{channel_slug}", response_model=SubscriptionRead)
def unsubscribe(
    channel_slug: str,
    principal: Annotated[UserPrincipal, Depends(require_csrf_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> SubscriptionRead:
    channel = resolve_channel(session, channel_slug)
    subscription = owned_subscription(session, principal.user_id, channel.id)
    if subscription is not None and subscription.enabled:
        subscription.enabled = False
        session.commit()
    return subscription_read(channel, subscription)
