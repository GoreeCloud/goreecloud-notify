"""Add human credential hashes and opaque web sessions.

Revision ID: 0002_human_authentication
Revises: 0001_milestone_2_baseline
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_human_authentication"
down_revision: Union[str, None] = "0001_milestone_2_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=512), nullable=True))
    op.create_table(
        "web_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"], unique=False)
    op.create_index("ix_web_sessions_session_digest", "web_sessions", ["session_digest"], unique=True)
    op.create_index("ix_web_sessions_last_seen_at", "web_sessions", ["last_seen_at"], unique=False)
    op.create_index("ix_web_sessions_expires_at", "web_sessions", ["expires_at"], unique=False)
    op.create_index("ix_web_sessions_revoked_at", "web_sessions", ["revoked_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_web_sessions_revoked_at", table_name="web_sessions")
    op.drop_index("ix_web_sessions_expires_at", table_name="web_sessions")
    op.drop_index("ix_web_sessions_last_seen_at", table_name="web_sessions")
    op.drop_index("ix_web_sessions_session_digest", table_name="web_sessions")
    op.drop_index("ix_web_sessions_user_id", table_name="web_sessions")
    op.drop_table("web_sessions")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_hash")
