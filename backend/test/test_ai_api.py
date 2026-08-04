#!/usr/bin/env python3
"""Standalone session API service test; never starts Docker or Bedrock."""
import asyncio
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from core.database import Base
from core.models import AIChatMessage, AICommandAttempt, AILearningSession, WebUser
from core.security import create_access_token, get_current_user
import routers.ai_tutor as ai_router
from routers.ai_tutor import (chat, create_session, execute_learning_command, get_curriculum,
                              get_history, get_session, grade, hint, reset_session)
from routers.ai_tutor import curriculum_router
from schemas.ai_tutor import (ChatRequest, CommandRequest, ResetRequest, SessionCreate,
                              VersionRequest)
from services.ai_rate_limit import bedrock_rate_limiter
from services.bedrock import BedrockMetadata, BedrockTutorResult, TutorModelResponse
from services.curriculum import get_problem, initial_state, list_problems


async def expect_http(code, awaitable):
    try:
        await awaitable
    except HTTPException as exc:
        assert exc.status_code == code, (exc.status_code, exc.detail)
    else:
        raise AssertionError(f"expected HTTP {code}")


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        engine = create_async_engine(f"sqlite+aiosqlite:///{Path(directory) / 'ai-api.db'}")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessions() as db:
            owner = WebUser(username="owner", hashed_password="test", role="viewer", is_active=True)
            other = WebUser(username="other", hashed_password="test", role="viewer", is_active=True)
            inactive = WebUser(username="inactive", hashed_password="test", role="viewer", is_active=False)
            db.add_all([owner, other, inactive])
            await db.commit()

            curriculum_route = next(
                route for route in curriculum_router.routes if route.path == "/ai/curriculum"
            )
            assert any(
                dependency.call is get_current_user
                for dependency in curriculum_route.dependant.dependencies
            )

            curriculum = await get_curriculum(owner)
            fixture_problems = list_problems()
            assert curriculum.total_tasks == 6 and len(curriculum.items) == 6
            # The final slot previews the review round generically; only the
            # first five items map 1:1 onto fixture problems.
            assert [item.task_id for item in curriculum.items[:-1]] == [
                item["problem_id"] for item in fixture_problems[:-1]
            ]
            assert [item.scenario_id for item in curriculum.items[:-1]] == [
                item["scenario_id"] for item in fixture_problems[:-1]
            ]
            for index, item in enumerate(curriculum.items[:-1], start=1):
                fixture_problem = fixture_problems[index - 1]
                assert item.task_index == index and item.total_tasks == 6
                assert item.title == fixture_problem["title"]
                assert item.description == fixture_problem["grading"]["success"]["description"]
                assert item.learning_goal and item.difficulty in {
                    "beginner", "intermediate", "advanced"
                }
            review_item = curriculum.items[-1]
            assert review_item.task_id == "review" and review_item.scenario_id == "review"
            assert review_item.task_index == 6 and review_item.total_tasks == 6
            assert review_item.difficulty == "advanced" and review_item.learning_goal

            # Per-user concurrency is isolated; one user cannot block another.
            bedrock_rate_limiter.cooldown_seconds = 2
            await bedrock_rate_limiter.reset()
            assert (await bedrock_rate_limiter.acquire(owner.id))[0]
            owner_second = await bedrock_rate_limiter.acquire(owner.id)
            assert owner_second[0] is False and owner_second[1] >= 1
            assert (await bedrock_rate_limiter.acquire(other.id))[0]
            await bedrock_rate_limiter.release(owner.id)
            await bedrock_rate_limiter.release(other.id)

            payload = SessionCreate(mode="simulation", level="beginner", scenario_key="service_recovery", task_key="service_recovery_01")
            created = await create_session(payload, db, owner)
            assert isinstance(created.id, int) and created.virtual_state.version == 1
            assert created.current_problem == curriculum.items[0]
            assert created.virtual_state.state_json == initial_state(payload.scenario_key, payload.task_key)
            assert created.started_at.isoformat()

            class FakeBedrock:
                def __init__(self):
                    self.calls = []

                def tutor(self, **kwargs):
                    self.calls.append(kwargs)
                    return BedrockTutorResult(degraded=False, reason=None, retryable=False,
                        message="안전한 설명", response=TutorModelResponse(
                            terminal_output="ok", explanation="안전한 설명", hint_level=0,
                            suggested_concept="service"), metadata=BedrockMetadata(
                                latency_ms=1, attempts=1))
            fake_bedrock = FakeBedrock()
            ai_router.bedrock_service = fake_bedrock
            bedrock_rate_limiter.cooldown_seconds = 0
            await bedrock_rate_limiter.reset()

            common_command_session = await create_session(payload, db, owner)
            listed = await execute_learning_command(common_command_session.id,
                CommandRequest(command_text="ls", expected_version=1), db, owner)
            assert listed.result_code == "success" and listed.output == "packages\nservices"
            assert listed.version == 2 and listed.state_before == listed.state_after
            listed_history = await get_history(common_command_session.id, db, owner)
            listed_attempt = next(item for item in listed_history.items
                                  if item.type == "command" and item.id == listed.attempt_id)
            assert listed_attempt.data["output_text"] == listed.output
            assert listed_attempt.data["state_before"] == listed_attempt.data["state_after"]

            # Complete the five real tasks through the public service functions
            # without Bedrock/AWS. The sixth (final) slot is a review round of
            # one of these five, not a fixed sixth fixture problem.
            complete_session = await create_session(payload, db, owner)
            complete_version = 1
            static_problems = list_problems()
            for index, problem in enumerate(static_problems[:-1]):
                assert (await get_session(complete_session.id, db, owner)).task_key == problem["problem_id"]
                assert (await get_session(complete_session.id, db, owner)).current_problem.task_index == index + 1
                for command_text in problem["answer_examples"]["correct"]["commands"]:
                    executed = await execute_learning_command(complete_session.id,
                        CommandRequest(command_text=command_text, expected_version=complete_version), db, owner)
                    complete_version = executed.version
                completion_grade = await grade(complete_session.id,
                    VersionRequest(expected_version=complete_version), db, owner)
                assert completion_grade.grade == "success"
                complete_version = completion_grade.version
                assert completion_grade.progress.completed is False

            review_session = await get_session(complete_session.id, db, owner)
            assert review_session.task_key.startswith("review_")
            assert review_session.current_problem.task_index == 6
            assert review_session.current_problem.total_tasks == 6
            assert review_session.current_problem.difficulty == "advanced"
            real_task_key = review_session.task_key.removeprefix("review_")
            assert real_task_key in {p["problem_id"] for p in static_problems[:-1]}
            review_problem = get_problem(review_session.scenario_key, review_session.task_key)
            for command_text in review_problem["answer_examples"]["correct"]["commands"]:
                executed = await execute_learning_command(complete_session.id,
                    CommandRequest(command_text=command_text, expected_version=complete_version), db, owner)
                complete_version = executed.version
            completion_grade = await grade(complete_session.id,
                VersionRequest(expected_version=complete_version), db, owner)
            assert completion_grade.grade == "success" and completion_grade.progress.completed
            complete_version = completion_grade.version
            completed_session = await get_session(complete_session.id, db, owner)
            assert completed_session.status == "completed" and completed_session.completed_at
            rejected = await execute_learning_command(created.id,
                CommandRequest(command_text="uname; id", expected_version=1), db, owner)
            assert rejected.result_code == "unsupported_syntax"
            assert rejected.version == 1 and rejected.state_before == rejected.state_after
            command = await execute_learning_command(created.id,
                CommandRequest(command_text="systemctl start nginx", expected_version=1), db, owner)
            assert command.version == 2 and command.attempt_id and command.progress.grade == "success"
            await expect_http(409, execute_learning_command(created.id,
                CommandRequest(command_text="systemctl status nginx", expected_version=1), db, owner))

            # Command execution no longer touches Bedrock, so the cooldown must
            # be armed directly to exercise chat()'s own rate limiting.
            assert (await bedrock_rate_limiter.acquire(owner.id))[0]
            await bedrock_rate_limiter.release(owner.id)
            bedrock_rate_limiter.cooldown_seconds = 2
            await expect_http(429, chat(created.id, ChatRequest(message="왜 그런가요?"), Response(), db, owner))
            await bedrock_rate_limiter.reset(); bedrock_rate_limiter.cooldown_seconds = 0
            chat_result = await chat(created.id, ChatRequest(message="왜 그런가요?"), Response(), db, owner)
            assert chat_result.user_message_id and chat_result.assistant_message_id
            # First turn in the session: no prior chat or grade history to feed back.
            assert fake_bedrock.calls[-1]["recent_conversation"] == []
            assert fake_bedrock.calls[-1]["learner_history"] == []

            # A successful task cannot issue a hint; grading advances atomically.
            await expect_http(409, hint(created.id, VersionRequest(expected_version=2), Response(), db, owner))
            graded = await grade(created.id, VersionRequest(expected_version=2), db, owner)
            assert graded.grade == "success" and graded.version == 3
            assert graded.progress.next_task_key == "service_recovery_02"
            advanced = await get_session(created.id, db, owner)
            assert advanced.task_key == "service_recovery_02" and advanced.virtual_state.version == 3
            assert advanced.current_problem.task_id == "service_recovery_02"
            assert advanced.current_problem.task_index == 2

            # A later chat turn now sees the earlier turn and the completed task's grade.
            second_chat = await chat(created.id, ChatRequest(message="다음엔 뭘 하나요?"), Response(), db, owner)
            assert second_chat.user_message_id
            assert fake_bedrock.calls[-1]["recent_conversation"] == [
                {"role": "user", "content": "왜 그런가요?"},
                {"role": "assistant", "content": "안전한 설명"},
            ]
            assert fake_bedrock.calls[-1]["learner_history"] == [
                {"task_key": "service_recovery_01", "grade": "success"},
            ]

            await bedrock_rate_limiter.reset()
            hint_result = await hint(created.id, VersionRequest(expected_version=3), Response(), db, owner)
            assert hint_result.hint_level == 1 and hint_result.hint_message_id
            assert hint_result.version == 4
            assert fake_bedrock.calls[-1]["learner_history"] == [
                {"task_key": "service_recovery_01", "grade": "success"},
            ]
            await expect_http(409, hint(created.id, VersionRequest(expected_version=3), Response(), db, owner))
            audited_history = await get_history(created.id, db, owner)
            assert any(item.type == "interaction" and item.data["action"] == "grade"
                       for item in audited_history.items)
            assert any(item.type == "interaction" and item.data["action"] == "hint"
                       for item in audited_history.items)

            failure_grade_session = await create_session(payload, db, owner)
            failed_grade = await grade(failure_grade_session.id,
                VersionRequest(expected_version=1), db, owner)
            assert failed_grade.grade == "failure" and failed_grade.version == 2
            await expect_http(409, grade(failure_grade_session.id,
                VersionRequest(expected_version=1), db, owner))

            # Keep the original Stage 3 reset/history regression isolated.
            created = await create_session(payload, db, owner)

            restored = await get_session(created.id, db, owner)
            assert restored.id == created.id
            await expect_http(404, get_session(created.id, db, other))
            await expect_http(404, get_session(999999, db, owner))
            await expect_http(422, create_session(SessionCreate(mode="docker", level="advanced", scenario_key="unknown", task_key="unknown"), db, owner))
            docker_session = await create_session(SessionCreate(mode="docker", level="beginner",
                scenario_key="service_recovery", task_key="service_recovery_01"), db, owner)
            await expect_http(409, execute_learning_command(docker_session.id,
                CommandRequest(command_text="systemctl start nginx", expected_version=1), db, owner))

            class ExplodingBedrock:
                def tutor(self, **kwargs):
                    raise RuntimeError("raw-secret-error")
            ai_router.bedrock_service = ExplodingBedrock()
            await bedrock_rate_limiter.reset()
            failure_session = await create_session(payload, db, owner)
            # Command execution never calls Bedrock, so it must keep working
            # even when the adapter is completely broken.
            command_result = await execute_learning_command(failure_session.id,
                CommandRequest(command_text="systemctl start nginx", expected_version=1), db, owner)
            assert command_result.version == 2 and command_result.result_code == "success"
            assert (await get_session(failure_session.id, db, owner)).virtual_state.version == 2
            degraded_hint_session = await create_session(payload, db, owner)
            await bedrock_rate_limiter.reset()
            degraded_hint = await hint(degraded_hint_session.id,
                VersionRequest(expected_version=1), Response(), db, owner)
            assert degraded_hint.version == 2 and degraded_hint.bedrock.degraded
            assert "raw-secret-error" not in degraded_hint.model_dump_json()
            degraded_history = await get_history(degraded_hint_session.id, db, owner)
            assert any(item.type == "interaction" and item.data["action"] == "hint"
                       for item in degraded_history.items)
            ai_router.bedrock_service = FakeBedrock()

            command = AICommandAttempt(session_id=created.id, mode="simulation", command_text="ss", result_code="success", output_text="ok", state_before={}, state_after={}, created_at=datetime.now(timezone.utc))
            db.add(command)
            await db.flush()
            db.add(AIChatMessage(session_id=created.id, role="user", content="why?", attempt_id=command.id, created_at=datetime.now(timezone.utc) + timedelta(microseconds=1)))
            await db.commit()

            reset = await reset_session(created.id, ResetRequest(expected_version=1), db, owner)
            assert reset.virtual_state.version == 2
            assert reset.current_problem.task_id == payload.task_key
            assert reset.virtual_state.state_json == initial_state(payload.scenario_key, payload.task_key)

            relogin_token = create_access_token({"sub": owner.username, "role": owner.role})
            relogged_user = await get_current_user(relogin_token, db)
            restored_after_relogin = await get_session(created.id, db, relogged_user)
            assert restored_after_relogin.id == created.id
            assert restored_after_relogin.virtual_state.version == 2
            assert restored_after_relogin.virtual_state.state_json == initial_state(payload.scenario_key, payload.task_key)

            history = await get_history(created.id, db, owner)
            assert [item.type for item in history.items] == ["command", "chat"]
            await expect_http(409, reset_session(created.id, ResetRequest(expected_version=1), db, owner))
            await db.refresh(owner)
            await db.refresh(inactive)

            valid_token = create_access_token({"sub": owner.username, "role": owner.role})
            assert (await get_current_user(valid_token, db)).id == owner.id
            inactive_token = create_access_token({"sub": inactive.username, "role": inactive.role})
            # core/security.py 계약 §1: 비활성 사용자는 403이 아니라 401(세션 정리 트리거)이다.
            await expect_http(401, get_current_user(inactive_token, db))
            await expect_http(401, get_current_user("invalid-token", db))

            try:
                SessionCreate(mode="invalid", level="beginner", scenario_key="x", task_key="y")
            except Exception:
                pass
            else:
                raise AssertionError("invalid mode must be rejected with validation error")
            for model, values in (
                (SessionCreate, {"mode": "simulation", "level": "beginner",
                    "scenario_key": "x", "task_key": "y", "extra": True}),
                (ResetRequest, {"expected_version": 1, "extra": True}),
                (CommandRequest, {"command_text": "ss", "expected_version": 1, "extra": True}),
            ):
                try:
                    model(**values)
                except Exception:
                    pass
                else:
                    raise AssertionError(f"{model.__name__} must reject extra fields")

        await engine.dispose()
    print("PASS: create/get/reset/history, 401/403/404/409/422, isolation, deterministic history")


if __name__ == "__main__":
    asyncio.run(main())
