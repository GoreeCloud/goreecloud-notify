"""Add production administrator authority and privileged audit events.

Revision ID: 0004_administrator_authorization
Revises: 0003_csrf_delivery_mutations
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_administrator_authorization"
down_revision: Union[str, None] = "0003_csrf_delivery_mutations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_users_is_admin", "users", ["is_admin"], unique=False)

    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("mechanism", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    op.create_index("ix_admin_audit_events_actor_user_id", "admin_audit_events", ["actor_user_id"])
    op.create_index("ix_admin_audit_events_action", "admin_audit_events", ["action"])
    op.create_index("ix_admin_audit_events_created_at", "admin_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_events_created_at", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_action", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_actor_user_id", table_name="admin_audit_events")
    op.drop_table("admin_audit_events")

    op.drop_index("ix_users_is_admin", table_name="users")
    op.drop_column("users", "is_admin")
