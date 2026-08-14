"""Add persistent login abuse-control state.

Revision ID: 0005_login_abuse_controls
Revises: 0004_administrator_authorization
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_login_abuse_controls"
down_revision: Union[str, None] = "0004_administrator_authorization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_rate_buckets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_digest", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_rate_buckets_key_digest", "login_rate_buckets", ["key_digest"], unique=True)
    op.create_index("ix_login_rate_buckets_scope", "login_rate_buckets", ["scope"])
    op.create_index("ix_login_rate_buckets_window_started_at", "login_rate_buckets", ["window_started_at"])
    op.create_index("ix_login_rate_buckets_blocked_until", "login_rate_buckets", ["blocked_until"])
    op.create_index("ix_login_rate_buckets_updated_at", "login_rate_buckets", ["updated_at"])

    op.create_table(
        "login_security_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("client_digest", sa.String(length=64), nullable=False),
        sa.Column("account_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_security_events_outcome", "login_security_events", ["outcome"])
    op.create_index("ix_login_security_events_client_digest", "login_security_events", ["client_digest"])
    op.create_index("ix_login_security_events_account_digest", "login_security_events", ["account_digest"])
    op.create_index("ix_login_security_events_created_at", "login_security_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_login_security_events_created_at", table_name="login_security_events")
    op.drop_index("ix_login_security_events_account_digest", table_name="login_security_events")
    op.drop_index("ix_login_security_events_client_digest", table_name="login_security_events")
    op.drop_index("ix_login_security_events_outcome", table_name="login_security_events")
    op.drop_table("login_security_events")

    op.drop_index("ix_login_rate_buckets_updated_at", table_name="login_rate_buckets")
    op.drop_index("ix_login_rate_buckets_blocked_until", table_name="login_rate_buckets")
    op.drop_index("ix_login_rate_buckets_window_started_at", table_name="login_rate_buckets")
    op.drop_index("ix_login_rate_buckets_scope", table_name="login_rate_buckets")
    op.drop_index("ix_login_rate_buckets_key_digest", table_name="login_rate_buckets")
    op.drop_table("login_rate_buckets")
