from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.models import (
    AIChatMessage,
    AICommandAttempt,
    AIInteractionAudit,
    AILearningSession,
    AIVirtualState,
    WebUser,
)
from core.security import get_current_user
from schemas.ai_tutor import (ChatRequest, ChatResponse, CommandRequest, CommandResponse,
    CurriculumResponse, GradeResponse, HintResponse, HistoryResponse, ProgressInfo,
    ResetRequest, SessionCreate, SessionResponse, VersionRequest)
from services.ai_rate_limit import bedrock_rate_limiter
from services.bedrock import BedrockService, BedrockTutorResult
from services.curriculum import (curriculum_info, get_problem, hint_for_problem,
                                 initial_state, next_problem, problem_info)
from services.task_grader import grade_problem
from services.virtual_linux import execute_command

router = APIRouter(prefix="/ai/sessions", tags=["AI Tutor"])
curriculum_router = APIRouter(prefix="/ai", tags=["AI Tutor"])
bedrock_service = BedrockService()


def _bedrock_dict(result: BedrockTutorResult) -> dict:
    return {
        "degraded": result.degraded, "reason": result.reason,
        "retryable": result.retryable, "message": result.message,
        "metadata": result.metadata.model_dump(),
    }


def _limited_bedrock() -> dict:
    return {"degraded": True, "reason": "rate_limited", "retryable": True,
            "message": "AI 설명 요청 간격이 너무 짧아 규칙 기반 결과를 제공합니다.", "metadata": {}}


def _adapter_fallback() -> dict:
    return {"degraded": True, "reason": "bedrock_adapter_error", "retryable": True,
            "message": "AI 설명을 불러오지 못해 규칙 기반 결과를 제공합니다.",
            "metadata": {}}


async def _call_bedrock(user_id: int, *, reject: bool = True, **kwargs) -> dict:
    acquired, retry_after = await bedrock_rate_limiter.acquire(user_id)
    if not acquired:
        if reject:
            raise HTTPException(429, "Bedrock request is busy or cooling down",
                                headers={"Retry-After": str(retry_after)})
        return _limited_bedrock()
    try:
        try:
            return _bedrock_dict(await run_in_threadpool(lambda: bedrock_service.tutor(**kwargs)))
        except Exception:
            return _adapter_fallback()
    finally:
        await bedrock_rate_limiter.release(user_id)


def _progress(grade: str, attempts: int, hint_level: int, following=None,
              completed: bool = False) -> ProgressInfo:
    return ProgressInfo(grade=grade, attempts=attempts, hint_level=hint_level,
        next_scenario_key=following["scenario_id"] if following else None,
        next_task_key=following["problem_id"] if following else None,
        next_level=following["difficulty"] if following else None, completed=completed)


async def _version_or_409(session: AILearningSession, expected: int) -> None:
    if session.virtual_state.version != expected:
        raise HTTPException(status.HTTP_409_CONFLICT, "Virtual state version conflict")


def _require_simulation(session: AILearningSession) -> None:
    if session.mode != "simulation":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This endpoint supports simulation sessions only")


async def _task_stats(db: AsyncSession, session: AILearningSession) -> tuple[int, int]:
    rows = (await db.execute(select(AIInteractionAudit).where(
        AIInteractionAudit.session_id == session.id,
        AIInteractionAudit.scenario_key == session.scenario_key,
        AIInteractionAudit.task_key == session.task_key,
    ))).scalars().all()
    attempts = sum(1 for row in rows if row.action == "grade")
    hints = [row.details_json.get("hint_level", 0) for row in rows if row.action == "hint"]
    return attempts, max(hints, default=0)


async def _owned_session(db: AsyncSession, session_id: int, user_id: int) -> AILearningSession:
    result = await db.execute(
        select(AILearningSession)
        .options(selectinload(AILearningSession.virtual_state))
        .where(AILearningSession.id == session_id, AILearningSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning session not found")
    return session


def _response(session: AILearningSession) -> SessionResponse:
    current_problem = problem_info(session.scenario_key, session.task_key)
    if current_problem is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Session fixture is unavailable")
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        mode=session.mode,
        level=session.level,
        scenario_key=session.scenario_key,
        task_key=session.task_key,
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        virtual_state=session.virtual_state,
        current_problem=current_problem,
    )


@curriculum_router.get("/curriculum", response_model=CurriculumResponse)
async def get_curriculum(
    current_user: WebUser = Depends(get_current_user),
):
    items = curriculum_info()
    return CurriculumResponse(total_tasks=len(items), items=items)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: WebUser = Depends(get_current_user),
):
    state = initial_state(request.scenario_key, request.task_key)
    if state is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown scenario/problem combination")

    learning_session = AILearningSession(
        user_id=current_user.id,
        mode=request.mode,
        level=request.level,
        scenario_key=request.scenario_key,
        task_key=request.task_key,
    )
    learning_session.virtual_state = AIVirtualState(state_json=state, version=1)
    db.add(learning_session)
    try:
        await db.commit()
        await db.refresh(learning_session)
    except Exception:
        await db.rollback()
        raise
    learning_session = await _owned_session(db, learning_session.id, current_user.id)
    return _response(learning_session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: WebUser = Depends(get_current_user),
):
    return _response(await _owned_session(db, session_id, current_user.id))


@router.post("/{session_id}/reset", response_model=SessionResponse)
async def reset_session(
    session_id: int,
    request: ResetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: WebUser = Depends(get_current_user),
):
    user_id = current_user.id
    learning_session = await _owned_session(db, session_id, user_id)
    reset_state = initial_state(learning_session.scenario_key, learning_session.task_key)
    if reset_state is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Session fixture is unavailable")

    result = await db.execute(
        update(AIVirtualState)
        .where(
            AIVirtualState.session_id == session_id,
            AIVirtualState.version == request.expected_version,
        )
        .values(
            state_json=reset_state,
            version=request.expected_version + 1,
            updated_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Virtual state version conflict")
    await db.commit()
    await db.refresh(learning_session.virtual_state)
    return _response(learning_session)


@router.get("/{session_id}/history", response_model=HistoryResponse)
async def get_history(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: WebUser = Depends(get_current_user),
):
    await _owned_session(db, session_id, current_user.id)
    commands = (
        await db.execute(select(AICommandAttempt).where(AICommandAttempt.session_id == session_id))
    ).scalars().all()
    chats = (
        await db.execute(select(AIChatMessage).where(AIChatMessage.session_id == session_id))
    ).scalars().all()
    audits = (
        await db.execute(select(AIInteractionAudit).where(AIInteractionAudit.session_id == session_id))
    ).scalars().all()
    items = [
        {
            "type": "command",
            "id": item.id,
            "created_at": item.created_at,
            "data": {
                "mode": item.mode,
                "command_text": item.command_text,
                "result_code": item.result_code,
                "output_text": item.output_text,
                "state_before": item.state_before,
                "state_after": item.state_after,
                "is_task_success": item.is_task_success,
            },
        }
        for item in commands
    ] + [
        {
            "type": "chat",
            "id": item.id,
            "created_at": item.created_at,
            "data": {"role": item.role, "content": item.content, "attempt_id": item.attempt_id},
        }
        for item in chats
    ] + [
        {
            "type": "interaction", "id": item.id, "created_at": item.created_at,
            "data": {"action": item.action, "scenario_key": item.scenario_key,
                     "task_key": item.task_key, "result_code": item.result_code,
                     "details": item.details_json},
        }
        for item in audits
    ]
    def sort_key(item: dict):
        created_at = item["created_at"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return (created_at.timestamp(), item["type"], item["id"])

    items.sort(key=sort_key)
    return HistoryResponse(session_id=session_id, items=items)


@router.post("/{session_id}/commands", response_model=CommandResponse)
async def execute_learning_command(session_id: int, request: CommandRequest,
    db: AsyncSession = Depends(get_db), current_user: WebUser = Depends(get_current_user)):
    session = await _owned_session(db, session_id, current_user.id)
    _require_simulation(session)
    if session.status == "completed":
        raise HTTPException(409, "Curriculum is completed")
    await _version_or_409(session, request.expected_version)
    # Command execution is silent by design: the deterministic simulator
    # decides the output, and Bedrock never comments on it here. AI advice
    # is only available through the separate /chat and /hints endpoints.
    execution = execute_command(session.virtual_state.state_json, request.command_text)
    attempt = AICommandAttempt(session_id=session.id, mode="simulation",
        command_text=request.command_text, result_code=execution.result_code,
        output_text=execution.output, state_before=execution.state_before,
        state_after=execution.state_after, is_task_success=False)
    db.add(attempt)
    if execution.result_code == "success":
        changed = await db.execute(update(AIVirtualState).where(
            AIVirtualState.session_id == session.id,
            AIVirtualState.version == request.expected_version).values(
            state_json=execution.state_after, version=request.expected_version + 1,
            updated_at=datetime.now(timezone.utc)))
        if changed.rowcount != 1:
            await db.rollback()
            raise HTTPException(409, "Virtual state version conflict")
    await db.commit()
    await db.refresh(attempt)
    await db.refresh(session.virtual_state)
    problem = get_problem(session.scenario_key, session.task_key)
    grade = grade_problem(problem, session.virtual_state.state_json).grade
    attempts, hint_level = await _task_stats(db, session)
    following = next_problem(session.scenario_key, session.task_key, grade=grade) if grade == "success" else None
    return CommandResponse(session_id=session.id, scenario_id=session.scenario_key,
        task_id=session.task_key, version=session.virtual_state.version,
        attempt_id=attempt.id, result_code=execution.result_code,
        output=execution.output, state_before=execution.state_before,
        state_after=execution.state_after,
        progress=_progress(grade, attempts, hint_level, following))


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat(session_id: int, request: ChatRequest, response: Response,
    db: AsyncSession = Depends(get_db), current_user: WebUser = Depends(get_current_user)):
    session = await _owned_session(db, session_id, current_user.id)
    _require_simulation(session)
    if session.status == "completed":
        raise HTTPException(409, "Curriculum is completed")
    problem = get_problem(session.scenario_key, session.task_key)
    grade = grade_problem(problem, session.virtual_state.state_json).grade
    result = await _call_bedrock(current_user.id, learner_level=session.level,
        problem=problem, state_summary=session.virtual_state.state_json, grade=grade,
        user_input=request.message)
    user_msg = AIChatMessage(session_id=session.id, role="user", content=request.message)
    assistant = AIChatMessage(session_id=session.id, role="assistant", content=result["message"])
    db.add_all([user_msg, assistant])
    await db.commit(); await db.refresh(user_msg); await db.refresh(assistant)
    attempts, hint_level = await _task_stats(db, session)
    following = next_problem(session.scenario_key, session.task_key, grade=grade) if grade == "success" else None
    return ChatResponse(session_id=session.id, scenario_id=session.scenario_key,
        task_id=session.task_key, version=session.virtual_state.version,
        user_message_id=user_msg.id, assistant_message_id=assistant.id,
        progress=_progress(grade, attempts, hint_level, following), bedrock=result)


@router.post("/{session_id}/hints", response_model=HintResponse)
async def hint(session_id: int, request: VersionRequest, response: Response,
    db: AsyncSession = Depends(get_db), current_user: WebUser = Depends(get_current_user)):
    session = await _owned_session(db, session_id, current_user.id)
    _require_simulation(session)
    if session.status == "completed": raise HTTPException(409, "Curriculum is completed")
    await _version_or_409(session, request.expected_version)
    problem = get_problem(session.scenario_key, session.task_key)
    current_grade = grade_problem(problem, session.virtual_state.state_json).grade
    if current_grade == "success":
        raise HTTPException(409, "Task is already successful")
    attempts, current_hint = await _task_stats(db, session)
    level = min(3, current_hint + 1)
    fixed = hint_for_problem(session.scenario_key, session.task_key, level)
    result = await _call_bedrock(current_user.id, learner_level=session.level,
        problem=problem, state_summary=session.virtual_state.state_json, grade="failure",
        user_input=f"규칙 기반 힌트 {level}: {fixed['text']}")
    hint_msg = AIChatMessage(session_id=session.id, role="hint", content=fixed["text"])
    assistant = AIChatMessage(session_id=session.id, role="assistant", content=result["message"])
    audit = AIInteractionAudit(session_id=session.id, action="hint",
        scenario_key=session.scenario_key, task_key=session.task_key, result_code="provided",
        details_json={"hint_level": level, "kind": fixed["kind"]})
    next_version = request.expected_version + 1
    changed = await db.execute(update(AIVirtualState).where(
        AIVirtualState.session_id == session.id,
        AIVirtualState.version == request.expected_version).values(
        version=next_version, updated_at=datetime.now(timezone.utc)))
    if changed.rowcount != 1:
        await db.rollback()
        raise HTTPException(409, "Virtual state version conflict")
    db.add_all([hint_msg, assistant, audit]); await db.commit()
    await db.refresh(hint_msg); await db.refresh(assistant)
    return HintResponse(session_id=session.id, scenario_id=session.scenario_key,
        task_id=session.task_key, version=next_version,
        hint_message_id=hint_msg.id, assistant_message_id=assistant.id,
        hint_level=level, hint=fixed["text"],
        progress=_progress(current_grade, attempts, level), bedrock=result)


@router.post("/{session_id}/grade", response_model=GradeResponse)
async def grade(session_id: int, request: VersionRequest,
    db: AsyncSession = Depends(get_db), current_user: WebUser = Depends(get_current_user)):
    session = await _owned_session(db, session_id, current_user.id)
    _require_simulation(session)
    if session.status == "completed": raise HTTPException(409, "Curriculum is completed")
    await _version_or_409(session, request.expected_version)
    attempts, hint_level = await _task_stats(db, session)
    problem = get_problem(session.scenario_key, session.task_key)
    commands = (await db.execute(select(AICommandAttempt.command_text).where(
        AICommandAttempt.session_id == session.id))).scalars().all()
    result = grade_problem(problem, session.virtual_state.state_json, commands,
        previous_attempts=attempts, hint_level=hint_level)
    old_scenario, old_task = session.scenario_key, session.task_key
    following = next_problem(old_scenario, old_task, grade=result.grade)
    completed = result.grade == "success" and following is None
    next_version = request.expected_version + 1
    target_state = (following["initial_state"]
                    if result.grade == "success" and not completed
                    else session.virtual_state.state_json)
    changed = await db.execute(update(AIVirtualState).where(
        AIVirtualState.session_id == session.id,
        AIVirtualState.version == request.expected_version).values(
        state_json=target_state, version=next_version,
        updated_at=datetime.now(timezone.utc)))
    if changed.rowcount != 1:
        await db.rollback()
        raise HTTPException(409, "Virtual state version conflict")
    if result.grade == "success":
        if completed:
            session.status = "completed"; session.completed_at = datetime.now(timezone.utc)
        else:
            session.scenario_key = following["scenario_id"]; session.task_key = following["problem_id"]
            session.level = following["difficulty"]
    session.virtual_state.version = next_version
    session.virtual_state.updated_at = datetime.now(timezone.utc)
    audit = AIInteractionAudit(session_id=session.id, action="grade", scenario_key=old_scenario,
        task_key=old_task, result_code=result.grade,
        details_json={"attempts": result.attempts, "hint_level": hint_level,
                      "next_scenario_id": following["scenario_id"] if following and result.grade == "success" else None,
                      "next_task_id": following["problem_id"] if following and result.grade == "success" else None,
                      "completed": completed})
    db.add(audit); await db.commit(); await db.refresh(audit)
    progress = _progress(result.grade, result.attempts, hint_level,
        following if result.grade == "success" else None, completed)
    return GradeResponse(session_id=session.id, scenario_id=old_scenario, task_id=old_task,
        version=next_version, grade_message_id=audit.id, grade=result.grade,
        description=result.description, progress=progress)
