#!/usr/bin/env python3
"""Standalone model contract test using only a temporary SQLite database."""
import asyncio
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from core.database import Base
from core.models import AIChatMessage, AICommandAttempt, AILearningSession, AIVirtualState, WebUser


async def main() -> None:
    expected = {
        AILearningSession: {"id", "user_id", "mode", "level", "scenario_key", "task_key", "status", "started_at", "completed_at"},
        AIVirtualState: {"id", "session_id", "state_json", "version", "updated_at"},
        AICommandAttempt: {"id", "session_id", "mode", "command_text", "result_code", "output_text", "state_before", "state_after", "is_task_success", "created_at"},
        AIChatMessage: {"id", "session_id", "role", "content", "attempt_id", "created_at"},
    }
    for model, columns in expected.items():
        assert columns == set(model.__table__.columns.keys())

    with tempfile.TemporaryDirectory() as directory:
        url = f"sqlite+aiosqlite:///{Path(directory) / 'ai-models.db'}"
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            user = WebUser(username="model_user", hashed_password="test", role="viewer", is_active=True)
            learning = AILearningSession(mode="simulation", level="beginner", scenario_key="service_recovery", task_key="service_recovery_01")
            learning.virtual_state = AIVirtualState(state_json={"safe": True, "nested": {"ports": [22]}}, version=1)
            user.ai_learning_sessions.append(learning)
            db.add(user)
            command = AICommandAttempt(
                mode="simulation",
                command_text="ss",
                result_code="success",
                output_text="22 listening",
                state_before={"checked": False},
                state_after={"checked": True},
            )
            learning.command_attempts.append(command)
            chat = AIChatMessage(role="assistant", content="SSH 포트를 확인했습니다.")
            command.chat_messages.append(chat)
            learning.chat_messages.append(chat)
            await db.commit()
            learning_id = learning.id
        async with sessions() as db:
            loaded = (
                await db.execute(
                    select(AILearningSession)
                    .options(
                        selectinload(AILearningSession.virtual_state),
                        selectinload(AILearningSession.command_attempts).selectinload(AICommandAttempt.chat_messages),
                    )
                    .where(AILearningSession.id == learning_id)
                )
            ).scalar_one()
            assert loaded.status == "in_progress"
            assert loaded.started_at is not None and loaded.started_at.isoformat()
            assert loaded.virtual_state.version == 1
            assert loaded.virtual_state.updated_at is not None and loaded.virtual_state.updated_at.isoformat()
            assert loaded.virtual_state.state_json == {"safe": True, "nested": {"ports": [22]}}
            assert len(loaded.command_attempts) == 1
            loaded_command = loaded.command_attempts[0]
            assert loaded_command.state_before == {"checked": False}
            assert loaded_command.state_after == {"checked": True}
            assert loaded_command.created_at is not None and loaded_command.created_at.isoformat()
            assert len(loaded_command.chat_messages) == 1
            loaded_chat = loaded_command.chat_messages[0]
            assert loaded_chat.session_id == loaded.id
            assert loaded_chat.attempt_id == loaded_command.id
            assert loaded_chat.created_at is not None and loaded_chat.created_at.isoformat()
        await engine.dispose()
    print("PASS: AI model defaults, relationships, FKs, JSON reload, and temporary SQLite persistence")


if __name__ == "__main__":
    asyncio.run(main())
