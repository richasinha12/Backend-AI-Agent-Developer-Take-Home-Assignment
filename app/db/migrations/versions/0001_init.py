"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-06-08

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("session_id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_created_at", "chat_sessions", ["created_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("chat_sessions.session_id"), index=True),
        sa.Column("user_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    op.create_table(
        "user_memory_kv",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("key", sa.String(length=128), nullable=False, index=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_memory_kv_user_id", "user_memory_kv", ["user_id"])
    op.create_index("ix_user_memory_kv_key", "user_memory_kv", ["key"])
    op.create_index("ix_user_memory_kv_updated_at", "user_memory_kv", ["updated_at"])

    op.create_table(
        "eval_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("user_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("groundedness", sa.Float(), nullable=False),
        sa.Column("relevance", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, index=True),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("tools_called", sqlite.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_eval_records_user_id", "eval_records", ["user_id"])
    op.create_index("ix_eval_records_session_id", "eval_records", ["session_id"])
    op.create_index("ix_eval_records_confidence", "eval_records", ["confidence"])
    op.create_index("ix_eval_records_flagged", "eval_records", ["flagged"])
    op.create_index("ix_eval_records_created_at", "eval_records", ["created_at"])


def downgrade() -> None:
    op.drop_table("eval_records")
    op.drop_table("user_memory_kv")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")

