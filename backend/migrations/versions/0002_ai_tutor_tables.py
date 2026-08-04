"""ai tutor: ai_learning_sessions, ai_virtual_states, ai_command_attempts,
ai_chat_messages, ai_interaction_audits

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-04

docs/ai-plan.md 의 AI 리눅스 학습 기능(backend/routers/ai_tutor.py, core/models.py)이
사용하는 테이블을 최초로 생성한다. 0001과 같은 멱등 패턴을 따른다: 이미 존재하는
테이블은 건드리지 않는다.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "ai_learning_sessions" not in existing_tables:
        op.create_table(
            "ai_learning_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("mode", sa.String(length=16), nullable=False),
            sa.Column("level", sa.String(length=16), nullable=False),
            sa.Column("scenario_key", sa.String(length=64), nullable=False),
            sa.Column("task_key", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["web_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_ai_learning_sessions_id", "ai_learning_sessions", ["id"]
        )
        op.create_index(
            "ix_ai_learning_sessions_user_id", "ai_learning_sessions", ["user_id"]
        )

    if "ai_virtual_states" not in existing_tables:
        op.create_table(
            "ai_virtual_states",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("state_json", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["session_id"], ["ai_learning_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_virtual_states_id", "ai_virtual_states", ["id"])
        op.create_index(
            "ix_ai_virtual_states_session_id",
            "ai_virtual_states",
            ["session_id"],
            unique=True,
        )

    if "ai_command_attempts" not in existing_tables:
        op.create_table(
            "ai_command_attempts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("mode", sa.String(length=16), nullable=False),
            sa.Column("command_text", sa.String(length=2048), nullable=False),
            sa.Column("result_code", sa.String(length=32), nullable=False),
            sa.Column("output_text", sa.Text(), nullable=False),
            sa.Column("state_before", sa.JSON(), nullable=False),
            sa.Column("state_after", sa.JSON(), nullable=False),
            sa.Column("is_task_success", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["session_id"], ["ai_learning_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_ai_command_attempts_id", "ai_command_attempts", ["id"]
        )
        op.create_index(
            "ix_ai_command_attempts_session_id", "ai_command_attempts", ["session_id"]
        )
        op.create_index(
            "ix_ai_command_attempts_created_at", "ai_command_attempts", ["created_at"]
        )

    if "ai_chat_messages" not in existing_tables:
        op.create_table(
            "ai_chat_messages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("attempt_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["session_id"], ["ai_learning_sessions.id"]),
            sa.ForeignKeyConstraint(["attempt_id"], ["ai_command_attempts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_chat_messages_id", "ai_chat_messages", ["id"])
        op.create_index(
            "ix_ai_chat_messages_session_id", "ai_chat_messages", ["session_id"]
        )
        op.create_index(
            "ix_ai_chat_messages_attempt_id", "ai_chat_messages", ["attempt_id"]
        )
        op.create_index(
            "ix_ai_chat_messages_created_at", "ai_chat_messages", ["created_at"]
        )

    if "ai_interaction_audits" not in existing_tables:
        op.create_table(
            "ai_interaction_audits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=16), nullable=False),
            sa.Column("scenario_key", sa.String(length=64), nullable=False),
            sa.Column("task_key", sa.String(length=64), nullable=False),
            sa.Column("result_code", sa.String(length=32), nullable=False),
            sa.Column("details_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["session_id"], ["ai_learning_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_ai_interaction_audits_id", "ai_interaction_audits", ["id"]
        )
        op.create_index(
            "ix_ai_interaction_audits_session_id",
            "ai_interaction_audits",
            ["session_id"],
        )
        op.create_index(
            "ix_ai_interaction_audits_created_at",
            "ai_interaction_audits",
            ["created_at"],
        )


def downgrade() -> None:
    op.drop_table("ai_interaction_audits")
    op.drop_table("ai_chat_messages")
    op.drop_table("ai_command_attempts")
    op.drop_table("ai_virtual_states")
    op.drop_table("ai_learning_sessions")
