"""Add privacy-minimized source-scoped notification idempotency.

Revision ID: 0006_notification_idempotency
Revises: 0005_login_abuse_controls
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_notification_idempotency"
down_revision: Union[str, None] = "0005_login_abuse_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("idempotency_digest", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_notification_source_idempotency",
        "notifications",
        ["source_id", "idempotency_digest"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notification_source_idempotency",
        "notifications",
        type_="unique",
    )
    op.drop_column("notifications", "idempotency_digest")
