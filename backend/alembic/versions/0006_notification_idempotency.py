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
    # Batch mode keeps this migration portable to the SQLite test/development
    # database while producing the same unique source/key constraint on target
    # databases such as PostgreSQL.
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(
            sa.Column("idempotency_digest", sa.String(length=64), nullable=True)
        )
        batch_op.create_unique_constraint(
            "uq_notification_source_idempotency",
            ["source_id", "idempotency_digest"],
        )


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint(
            "uq_notification_source_idempotency",
            type_="unique",
        )
        batch_op.drop_column("idempotency_digest")
