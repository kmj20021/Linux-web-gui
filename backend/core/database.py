"""
데이터베이스 설정 및 세션 관리
SQLAlchemy + SQLite 비동기 설정
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# 데이터베이스 URL (환경변수 또는 기본값)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./linux_web_gui.db"
) # DATABASE_URL을 주세요. 값이 없다면 환경 변수로 DATABASE_URL를 "sqlite+aiosqlite:///./linux_web_gui.db"를 임시로 사용하세요.

# 비동기 엔진 생성
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # SQL 로깅 (개발시 True)
    future=True, #최신 SQLAlchemy 2.0 스타일 사용
    pool_pre_ping=True, #데이터 보내기 전 연결 확인 (유효성 검사)
    pool_recycle=3600, #3600초(1시간) 마다 재 연결
    # SQLite의 경우 StaticPool 사용
    connect_args={"timeout": 30, "check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
)

# 비동기 세션 팩토리
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession, #비동기 전용 세션
    expire_on_commit=False, #커밋 후 객체 만료 방지
    autoflush=False, # 명령을 내릴때 마다 DB에 반영하는지?
    autocommit=False, # 명령을 내릴때 마다 자동으로 커밋하는지?
)

# Base 클래스 (모든 모델이 상속)
Base = declarative_base()

# 의존성: FastAPI에서 사용할 get_db
async def get_db():
    """FastAPI 의존성: 데이터베이스 세션 반환"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """데이터베이스 테이블 생성"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """데이터베이스 연결 종료"""
    await engine.dispose()
