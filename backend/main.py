"""
FastAPI 메인 진입점
라즈베리 파이 기반 Linux 웹 GUI 관리 시스템
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
import subprocess

# 로그 설정 (모든 임포트 전에 정의)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 라우터 임포트
try:
    from routers.cpu import router as cpu_router
    from routers.memory import router as memory_router
    from routers.process import router as process_router
    from routers.disk import router as disk_router
    from routers.websocket import router as websocket_router
    from routers.history import router as history_router
    from routers.auth import router as auth_router
    from routers.admin import router as admin_router
    logger_import_success = True
except ImportError as e:
    logger_import_success = False
    import traceback
    traceback.print_exc()

# shell 라우터는 독립적으로 임포트 (가상 셸 기능)
try:
    from routers.shell import router as shell_router
    shell_import_success = True
except ImportError as e:
    shell_import_success = False
    import traceback
    traceback.print_exc()

# network 라우터는 독립적으로 임포트 (실패해도 다른 라우터에 영향 없도록 분리)
try:
    from routers.network import router as network_router
    network_import_success = True
except ImportError as e:
    network_import_success = False
    import traceback
    traceback.print_exc()

# 데이터베이스 및 스케줄러 임포트
try:
    from core.database import init_db, close_db, AsyncSessionLocal, engine
    from core.models import WebUser
    from core.security import get_password_hash
    from services.scheduler import start_scheduler, stop_scheduler
    from sqlalchemy import select, text
    db_import_success = True
except ImportError as e:
    db_import_success = False
    logger.error(f"데이터베이스/스케줄러 임포트 실패: {e}")


async def ensure_web_users_columns():
    """
    기존 SQLite DB 파일에 web_users.created_by 컬럼이 없을 경우 ALTER TABLE 로 추가한다.
    SQLAlchemy 의 create_all() 은 이미 존재하는 테이블에 새 컬럼을 추가하지 않으므로,
    스키마 변경 후 첫 기동 시 한 번 수동 마이그레이션이 필요하다.
    이미 컬럼이 존재하면 예외가 발생하므로 try/except 로 안전하게 무시한다.
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE web_users ADD COLUMN created_by VARCHAR(64)")
            )
        logger.info("✅ web_users.created_by 컬럼 추가 완료")
    except Exception as e:
        # 이미 컬럼이 있으면 'duplicate column name' 에러 → 정상 케이스
        logger.info(f"ℹ️ web_users.created_by 컬럼 마이그레이션 스킵: {e}")


async def ensure_default_admin():
    """
    WebUser 테이블에 admin 계정이 없으면 기본 admin 계정을 생성한다.
    - username: admin
    - password: admin1234 (bcrypt 해시 저장)
    - role: admin
    이미 존재하면 아무 작업도 하지 않는다.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WebUser).where(WebUser.username == "admin")
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            logger.info("ℹ️ admin 계정이 이미 존재하여 시드 생성을 건너뜁니다")
            return

        admin = WebUser(
            username="admin",
            hashed_password=get_password_hash("admin1234"),
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        logger.info("✅ 기본 admin 계정 생성 완료 (username=admin)")

app = FastAPI(
    title="Linux Web GUI API",
    description="라즈베리 파이 기반 통합 관리 시스템 REST API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
if logger_import_success:
    app.include_router(auth_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(cpu_router, prefix="/api")
    app.include_router(memory_router, prefix="/api")
    app.include_router(process_router, prefix="/api")
    app.include_router(disk_router, prefix="/api")
    app.include_router(websocket_router)  # /ws/는 nginx에서 별도 설정
    app.include_router(history_router, prefix="/api")
    logger.info("✅ auth, admin, monitor, websocket, history 라우터 등록됨")
else:
    logger.warning("⚠️ 라우터 등록 실패")

# network 라우터 등록 (/api prefix)
if network_import_success:
    app.include_router(network_router, prefix="/api")
    logger.info("✅ network 라우터 등록됨")
else:
    logger.warning("⚠️ network 라우터 등록 실패")

# shell 라우터 등록 (라우터 자체에 /ws, /api 경로 포함)
if shell_import_success:
    app.include_router(shell_router)
    logger.info("✅ shell 라우터 등록됨 (WebSocket /ws/shell + REST /api/shell/*)")
else:
    logger.warning("⚠️ shell 라우터 등록 실패")

@app.get("/api/health", tags=["Health"])
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "message": "서버가 정상 작동 중입니다"}

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 이벤트"""
    logger.info("🚀 FastAPI 서버 시작")

    # Docker 이미지 확인
    try:
        result = subprocess.run(['docker', 'images', '-q', 'webterm:latest'],
                               capture_output=True, text=True, timeout=5)
        if result.stdout.strip():
            logger.info("✅ webterm Docker 이미지 확인됨")
        else:
            logger.warning("⚠️ webterm:latest 이미지가 없습니다. 'docker build -t webterm:latest -f Dockerfile.webterm .' 를 실행하세요.")
    except Exception as e:
        logger.warning(f"⚠️ Docker 확인 실패: {e}")

    # 데이터베이스 초기화 (테이블 생성)
    if db_import_success:
        try:
            await init_db()
            logger.info("✅ 데이터베이스 접속 및 테이블 생성 완료")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {e}")

        # 기존 DB 파일에 신규 컬럼이 없을 경우를 위한 마이그레이션
        try:
            await ensure_web_users_columns()
        except Exception as e:
            logger.error(f"❌ web_users 컬럼 마이그레이션 실패: {e}")

        # 기본 admin 계정 시드 (없을 때만 생성)
        try:
            await ensure_default_admin()
        except Exception as e:
            logger.error(f"❌ 기본 admin 계정 시드 실패: {e}")
    
    # 스케줄러 시작 (1분 간격 스냅샷 저장)
    if db_import_success:
        try:
            start_scheduler()
            logger.info("✅ 백그라운드 스케줄러 시작됨")
        except Exception as e:
            logger.error(f"❌ 스케줄러 시작 실패: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 이벤트"""
    logger.info("🛑 FastAPI 서버 종료")
    
    # 스케줄러 중지
    if db_import_success:
        try:
            stop_scheduler()
            logger.info("✅ 백그라운드 스케줄러 중지됨")
        except Exception as e:
            logger.error(f"❌ 스케줄러 중지 실패: {e}")
    
    # 데이터베이스 연결 해제
    if db_import_success:
        try:
            await close_db()
            logger.info("✅ 데이터베이스 연결 해제됨")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 해제 실패: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
