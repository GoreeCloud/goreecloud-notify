"""Milestone 2 baseline schema before human authentication.

Revision ID: 0001_milestone_2_baseline
Revises: None
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_milestone_2_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "service_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_service_identities_name", "service_identities", ["name"], unique=True)

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_channels_slug", "channels", ["slug"], unique=True)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("platform", sa.String(length=60), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "service_identity_id",
            sa.Integer(),
            sa.ForeignKey("service_identities.id"),
            nullable=True,
        ),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_service_identity_id", "sources", ["service_identity_id"], unique=False)
    op.create_index("ix_sources_slug", "sources", ["slug"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "channel_id", name="uq_subscription_user_channel"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_channel_id", "subscriptions", ["channel_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id"), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_source_id", "notifications", ["source_id"], unique=False)
    op.create_index("ix_notifications_channel_id", "notifications", ["channel_id"], unique=False)
    op.create_index("ix_notifications_severity", "notifications", ["severity"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)

    op.create_table(
        "deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notification_id", sa.Integer(), sa.ForeignKey("notifications.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("notification_id", "user_id", name="uq_delivery_notification_user"),
    )
    op.create_index("ix_deliveries_notification_id", "deliveries", ["notification_id"], unique=False)
    op.create_index("ix_deliveries_user_id", "deliveries", ["user_id"], unique=False)
    op.create_index("ix_deliveries_device_id", "deliveries", ["device_id"], unique=False)

    op.create_table(
        "access_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "service_identity_id",
            sa.Integer(),
            sa.ForeignKey("service_identities.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("token_digest", sa.String(length=255), nullable=False, unique=True),
        sa.Column("scope", sa.String(length=500), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_access_tokens_service_identity_id",
        "access_tokens",
        ["service_identity_id"],
        unique=False,
    )

    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_preference_user_key"),
    )
    op.create_index("ix_preferences_user_id", "preferences", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_preferences_user_id", table_name="preferences")
    op.drop_table("preferences")
    op.drop_index("ix_access_tokens_service_identity_id", table_name="access_tokens")
    op.drop_table("access_tokens")
    op.drop_index("ix_deliveries_device_id", table_name="deliveries")
    op.drop_index("ix_deliveries_user_id", table_name="deliveries")
    op.drop_index("ix_deliveries_notification_id", table_name="deliveries")
    op.drop_table("deliveries")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_severity", table_name="notifications")
    op.drop_index("ix_notifications_channel_id", table_name="notifications")
    op.drop_index("ix_notifications_source_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_subscriptions_channel_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_sources_slug", table_name="sources")
    op.drop_index("ix_sources_service_identity_id", table_name="sources")
    op.drop_table("sources")
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_table("devices")
    op.drop_index("ix_channels_slug", table_name="channels")
    op.drop_table("channels")
    op.drop_index("ix_service_identities_name", table_name="service_identities")
    op.drop_table("service_identities")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
