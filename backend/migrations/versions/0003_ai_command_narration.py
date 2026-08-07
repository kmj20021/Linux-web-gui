"""ai command narration: ai_command_attempts.narration_text

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-07

미지원/무관 명령에 대해 AI(Bedrock)가 생성한 표시용 나레이션 텍스트를 저장하는
nullable 컬럼을 추가한다. 결정론적 시뮬레이터 원문(`output_text`)은 그대로 두고
별도 컬럼에 저장해서 채점(task_grader.py)이 여전히 이 컬럼을 전혀 읽지 않는다는
경계를 유지한다. 0001/0002와 같은 멱등 패턴을 따른다.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ai_command_attempts" not in set(inspector.get_table_names()):
        return
    columns = {c["name"] for c in inspector.get_columns("ai_command_attempts")}
    if "narration_text" not in columns:
        with op.batch_alter_table("ai_command_attempts") as batch_op:
            batch_op.add_column(sa.Column("narration_text", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ai_command_attempts") as batch_op:
        batch_op.drop_column("narration_text")
