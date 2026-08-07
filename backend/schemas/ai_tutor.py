from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["docker", "simulation"]
    level: Literal["beginner", "intermediate", "advanced"]
    scenario_key: str = Field(min_length=1, max_length=64)
    task_key: str = Field(min_length=1, max_length=64)


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class VirtualStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    state_json: dict[str, Any]
    version: int
    updated_at: datetime


class CurrentProblemInfo(BaseModel):
    scenario_id: str
    task_id: str
    title: str
    description: str
    learning_goal: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    total_tasks: int
    task_index: int


class CurriculumResponse(BaseModel):
    total_tasks: int
    items: list[CurrentProblemInfo]


class SessionResponse(BaseModel):
    id: int
    user_id: int
    mode: str
    level: str
    scenario_key: str
    task_key: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    virtual_state: VirtualStateResponse
    current_problem: CurrentProblemInfo


class HistoryItem(BaseModel):
    type: Literal["command", "chat", "interaction"]
    id: int
    created_at: datetime
    data: dict[str, Any]


class HistoryResponse(BaseModel):
    session_id: int
    items: list[HistoryItem]


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_text: str = Field(min_length=1, max_length=2048, pattern=r".*\S.*")
    expected_version: int = Field(ge=1)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000, pattern=r".*\S.*")


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class BedrockInfo(BaseModel):
    degraded: bool
    reason: str | None
    retryable: bool
    message: str
    metadata: dict[str, Any]


class ProgressInfo(BaseModel):
    grade: Literal["success", "partial", "failure"]
    attempts: int
    hint_level: int
    next_scenario_key: str | None
    next_task_key: str | None
    next_level: str | None
    completed: bool


class CommandResponse(BaseModel):
    session_id: int
    scenario_id: str
    task_id: str
    version: int
    attempt_id: int
    result_code: str
    output: str
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    progress: ProgressInfo


class NarrationInfo(BaseModel):
    degraded: bool
    reason: str | None
    terminal_output: str
    metadata: dict[str, Any]


class NarrateResponse(BaseModel):
    session_id: int
    attempt_id: int
    narration: NarrationInfo


class ChatResponse(BaseModel):
    session_id: int
    scenario_id: str
    task_id: str
    version: int
    user_message_id: int
    assistant_message_id: int
    progress: ProgressInfo
    bedrock: BedrockInfo


class HintResponse(BaseModel):
    session_id: int
    scenario_id: str
    task_id: str
    version: int
    hint_message_id: int
    assistant_message_id: int | None
    hint_level: int
    hint: str
    progress: ProgressInfo
    bedrock: BedrockInfo


class GradeResponse(BaseModel):
    session_id: int
    scenario_id: str
    task_id: str
    version: int
    grade_message_id: int
    grade: Literal["success", "partial", "failure"]
    description: str
    progress: ProgressInfo
