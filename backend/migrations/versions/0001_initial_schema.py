"""initial schema: monitor_snapshots, web_users(created_by 포함), login_logs

Revision ID: 0001
Revises:
Create Date: 2026-07-30

DB-01: 현재 ORM 모델(core/models.py)의 스키마를 최초 리비전으로 고정한다.
DEC-01 에 따라 사용자 식별 컬럼은 `username` 을 유지한다(login_id 로 rename 하지 않음).

이 리비전은 과거 create_all + ad-hoc ALTER 로 이미 테이블이 만들어졌으나
alembic_version 이 없는 기존 DB 에도 안전하게 적용되도록 멱등적으로 작성한다:
존재하는 테이블/컬럼은 건드리지 않고, 없는 것만 생성한다.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "monitor_snapshots" not in existing_tables:
        op.create_table(
            "monitor_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cpu_total", sa.Float(), nullable=False),
            sa.Column("cpu_per_core", sa.JSON(), nullable=False),
            sa.Column("core_count", sa.Integer(), nullable=False),
            sa.Column("load_avg", sa.JSON(), nullable=False),
            sa.Column("mem_total_gb", sa.Float(), nullable=False),
            sa.Column("mem_used_gb", sa.Float(), nullable=False),
            sa.Column("mem_free_gb", sa.Float(), nullable=False),
            sa.Column("mem_buffers_gb", sa.Float(), nullable=False),
            sa.Column("mem_cached_gb", sa.Float(), nullable=False),
            sa.Column("mem_usage_pct", sa.Float(), nullable=False),
            sa.Column("top_processes", sa.JSON(), nullable=False),
            sa.Column(
                "recorded_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_monitor_snapshots_id", "monitor_snapshots", ["id"])
        op.create_index(
            "ix_monitor_snapshots_recorded_at", "monitor_snapshots", ["recorded_at"]
        )

    if "web_users" not in existing_tables:
        op.create_table(
            "web_users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=16), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("created_by", sa.String(length=64), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_web_users_id", "web_users", ["id"])
        op.create_index("ix_web_users_username", "web_users", ["username"], unique=True)
    else:
        # 기존 테이블에 created_by 가 없으면(과거 ad-hoc ALTER 이전 상태) 추가한다.
        web_user_columns = {c["name"] for c in inspector.get_columns("web_users")}
        if "created_by" not in web_user_columns:
            with op.batch_alter_table("web_users") as batch_op:
                batch_op.add_column(
                    sa.Column("created_by", sa.String(length=64), nullable=True)
                )

    if "login_logs" not in existing_tables:
        op.create_table(
            "login_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("role", sa.String(length=16), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_login_logs_id", "login_logs", ["id"])
        op.create_index("ix_login_logs_username", "login_logs", ["username"])
        op.create_index("ix_login_logs_created_at", "login_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("login_logs")
    op.drop_table("web_users")
    op.drop_table("monitor_snapshots")
