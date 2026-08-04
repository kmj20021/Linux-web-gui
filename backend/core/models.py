"""
SQLAlchemy ORM 모델
모니터링 스냅샷 데이터 저장
"""
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
from datetime import datetime, timezone


class MonitorSnapshot(Base):
    """
    시스템 모니터링 스냅샷 (1분 단위 저장)
    
    설계서 ERD 기준:
    - cpu_total: 전체 CPU 사용률
    - cpu_per_core: 코어별 CPU 사용률 (JSON)
    - core_count: 총 코어 수
    - load_avg: 부하 평균 (JSON)
    - mem_total_gb: 전체 메모리 GB
    - mem_used_gb: 사용 메모리 GB
    - mem_free_gb: 여유 메모리 GB
    - mem_buffers_gb: 버퍼 메모리 GB
    - mem_cached_gb: 캐시 메모리 GB
    - mem_usage_pct: 메모리 사용률
    - top_processes: 상위 프로세스 (JSON)
    - recorded_at: 기록 시간
    """
    
    __tablename__ = "monitor_snapshots"
    
    # 기본키
    id = Column(Integer, primary_key=True, index=True)
    
    # CPU 메트릭
    cpu_total = Column(Float, nullable=False)
    cpu_per_core = Column(JSON, nullable=False)  # [0.0, 1.5, 2.1, ...] 리스트
    core_count = Column(Integer, nullable=False)
    load_avg = Column(JSON, nullable=False)  # [load_1min, load_5min, load_15min]
    
    # 메모리 메트릭
    mem_total_gb = Column(Float, nullable=False)
    mem_used_gb = Column(Float, nullable=False)
    mem_free_gb = Column(Float, nullable=False)
    mem_buffers_gb = Column(Float, nullable=False)
    mem_cached_gb = Column(Float, nullable=False)
    mem_usage_pct = Column(Float, nullable=False)
    
    # 프로세스 정보 (상위 5개)
    top_processes = Column(JSON, nullable=False)  # [{"pid": ..., "name": ..., "cpu_pct": ..., "mem_pct": ...}, ...]
    
    # 타임스탬프
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(), #파이썬의 시간이 아닌 DB의 현재 시간 사용
        nullable=False,
        index=True  # 조회 성능 개선
    )
    
    def __repr__(self): #출력 형식 지정
        return f"<MonitorSnapshot(id={self.id}, cpu_total={self.cpu_total}, recorded_at={self.recorded_at})>"
    
    def to_dict(self):
        """모델을 딕셔너리로 변환"""
        return {
            "id": self.id,
            "cpu_total": self.cpu_total,
            "cpu_per_core": self.cpu_per_core,
            "core_count": self.core_count,
            "load_avg": self.load_avg,
            "mem_total_gb": self.mem_total_gb,
            "mem_used_gb": self.mem_used_gb,
            "mem_free_gb": self.mem_free_gb,
            "mem_buffers_gb": self.mem_buffers_gb,
            "mem_cached_gb": self.mem_cached_gb,
            "mem_usage_pct": self.mem_usage_pct,
            "top_processes": self.top_processes,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class WebUser(Base):
    """
    웹 사용자 계정 (리눅스 시스템 계정과 완전히 분리)

    - id: 기본키
    - username: 로그인 아이디 (유니크)
    - hashed_password: bcrypt 해시된 비밀번호
    - role: "admin" 또는 "viewer"
    - is_active: 계정 활성 상태
    - created_at: 생성 시각
    - created_by: 이 계정을 생성한 admin 의 username
                  (자가 회원가입 계정은 NULL)
    """

    __tablename__ = "web_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="viewer")  # "admin" | "viewer"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by = Column(String(64), nullable=True)

    ai_learning_sessions = relationship(
        "AILearningSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<WebUser(id={self.id}, username={self.username}, role={self.role})>"

    def to_dict(self):
        """모델을 딕셔너리로 변환 (해시된 비밀번호는 제외)"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


class LoginLog(Base):
    """
    로그인 이벤트 감사 로그

    - id: 기본키
    - username: 로그인한 사용자명
    - role: 로그인 시점의 사용자 role
    - ip_address: 클라이언트 IP (없으면 None)
    - created_at: 로그인 발생 시각
    """

    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self):
        return f"<LoginLog(id={self.id}, username={self.username}, created_at={self.created_at})>"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AILearningSession(Base):
    """
    AI 리눅스 학습 세션 (docs/ai-plan.md)

    - user_id: 세션 소유자 (WebUser)
    - mode: "docker" | "simulation" (MVP는 simulation만 실제 실행 지원)
    - level: "beginner" | "intermediate" | "advanced"
    - scenario_key / task_key: 커리큘럼 fixture의 시나리오·문제 식별자
    - status: "in_progress" | "completed"
    """

    __tablename__ = "ai_learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("web_users.id"), nullable=False, index=True)
    mode = Column(String(16), nullable=False)
    level = Column(String(16), nullable=False)
    scenario_key = Column(String(64), nullable=False)
    task_key = Column(String(64), nullable=False)
    status = Column(String(16), nullable=False, default="in_progress")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("WebUser", back_populates="ai_learning_sessions")
    virtual_state = relationship(
        "AIVirtualState", back_populates="session", uselist=False,
        cascade="all, delete-orphan",
    )
    command_attempts = relationship(
        "AICommandAttempt", back_populates="session",
        cascade="all, delete-orphan", order_by="AICommandAttempt.id",
    )
    chat_messages = relationship(
        "AIChatMessage", back_populates="session",
        cascade="all, delete-orphan", order_by="AIChatMessage.id",
    )

    def __repr__(self):
        return f"<AILearningSession(id={self.id}, user_id={self.user_id}, status={self.status})>"


class AIVirtualState(Base):
    """세션당 정확히 하나, 가상 리눅스 상태(JSON)와 낙관적 잠금용 version."""

    __tablename__ = "ai_virtual_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("ai_learning_sessions.id"), nullable=False, unique=True, index=True
    )
    state_json = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    session = relationship("AILearningSession", back_populates="virtual_state")

    def __repr__(self):
        return f"<AIVirtualState(id={self.id}, session_id={self.session_id}, version={self.version})>"


class AICommandAttempt(Base):
    """학습자가 입력한 명령과 시뮬레이터 실행 결과(before/after 가상 상태)."""

    __tablename__ = "ai_command_attempts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ai_learning_sessions.id"), nullable=False, index=True)
    mode = Column(String(16), nullable=False)
    command_text = Column(String(2048), nullable=False)
    result_code = Column(String(32), nullable=False)
    output_text = Column(Text, nullable=False)
    state_before = Column(JSON, nullable=False)
    state_after = Column(JSON, nullable=False)
    is_task_success = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    session = relationship("AILearningSession", back_populates="command_attempts")
    chat_messages = relationship("AIChatMessage", back_populates="attempt")

    def __repr__(self):
        return f"<AICommandAttempt(id={self.id}, session_id={self.session_id}, result_code={self.result_code})>"


class AIChatMessage(Base):
    """세션의 대화 기록: 사용자 메시지, Bedrock 응답, 규칙 기반 힌트."""

    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ai_learning_sessions.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # "user" | "assistant" | "hint"
    content = Column(Text, nullable=False)
    attempt_id = Column(Integer, ForeignKey("ai_command_attempts.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    session = relationship("AILearningSession", back_populates="chat_messages")
    attempt = relationship("AICommandAttempt", back_populates="chat_messages")

    def __repr__(self):
        return f"<AIChatMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"


class AIInteractionAudit(Base):
    """힌트 요청·채점 등 학습 상호작용 감사 로그 (진행률 계산과 이력 조회에 사용)."""

    __tablename__ = "ai_interaction_audits"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ai_learning_sessions.id"), nullable=False, index=True)
    action = Column(String(16), nullable=False)  # "hint" | "grade"
    scenario_key = Column(String(64), nullable=False)
    task_key = Column(String(64), nullable=False)
    result_code = Column(String(32), nullable=False)
    details_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<AIInteractionAudit(id={self.id}, session_id={self.session_id}, action={self.action})>"
