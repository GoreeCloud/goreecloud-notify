"""Bind CSRF tokens to human web sessions.

Revision ID: 0003_csrf_delivery_mutations
Revises: 0002_human_authentication
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_csrf_delivery_mutations"
down_revision: Union[str, None] = "0002_human_authentication"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("web_sessions") as batch_op:
        batch_op.add_column(sa.Column("csrf_token", sa.String(length=64), nullable=True))

    connection = op.get_bind()
    session_ids = connection.execute(sa.text("SELECT id FROM web_sessions")).scalars().all()
    revoke_session = sa.text(
        "UPDATE web_sessions "
        "SET csrf_token = :csrf_token, revoked_at = COALESCE(revoked_at, :revoked_at) "
        "WHERE id = :session_id"
    ).bindparams(
        sa.bindparam("revoked_at", type_=sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    for session_id in session_ids:
        connection.execute(
            revoke_session,
            {
                "csrf_token": secrets.token_urlsafe(32),
                "revoked_at": now,
                "session_id": session_id,
            },
        )

    with op.batch_alter_table("web_sessions") as batch_op:
        batch_op.alter_column(
            "csrf_token",
            existing_type=sa.String(length=64),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("web_sessions") as batch_op:
        batch_op.drop_column("csrf_token")
