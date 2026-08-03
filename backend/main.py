"""
FastAPI 메인 진입점
라즈베리 파이 기반 Linux 웹 GUI 관리 시스템
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
import subprocess

from core.security import validate_secret_key

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
    from core.database import close_db, engine
    from core.db_migrations import run_migrations
    from services.scheduler import start_scheduler, stop_scheduler
    db_import_success = True
except ImportError as e:
    db_import_success = False
    logger.error(f"데이터베이스/스케줄러 임포트 실패: {e}")


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
    # Validate before Docker, database, scheduler, or process side effects.
    validate_secret_key()
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

    # 데이터베이스 스키마 마이그레이션 (DB-01)
    # 임의 ALTER TABLE 대신 버전 관리된 Alembic 마이그레이션을 head 까지 적용한다.
    # 스키마 오류는 숨기지 않고 시작을 실패시킨다(fail-closed).
    if db_import_success:
        await asyncio.to_thread(run_migrations)
        logger.info("✅ 데이터베이스 마이그레이션 완료 (alembic head)")

    # 단일 메트릭 수집기 시작 (PERF-01: 공유 fan-out 소스)
    try:
        from services.metrics_collector import get_collector
        await get_collector().start()
        logger.info("✅ 메트릭 수집기 시작됨")
    except Exception as e:
        logger.error(f"❌ 메트릭 수집기 시작 실패: {e}")

    # 스케줄러 시작 (1분 간격 스냅샷 저장)
    if db_import_success:
        try:
            start_scheduler()
            logger.info("✅ 백그라운드 스케줄러 시작됨")
        except Exception as e:
            logger.error(f"❌ 스케줄러 시작 실패: {e}")

    # 데모 프로세스 워치독 시작
    try:
        from services.demo_procs import start_demo_processes
        start_demo_processes()
        logger.info("✅ 데모 프로세스 워치독 시작됨")
    except Exception as e:
        logger.error(f"❌ 데모 프로세스 워치독 시작 실패: {e}")

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

    # 메트릭 수집기 중지 (PERF-01)
    try:
        from services.metrics_collector import get_collector
        await get_collector().stop()
        logger.info("✅ 메트릭 수집기 중지됨")
    except Exception as e:
        logger.error(f"❌ 메트릭 수집기 중지 실패: {e}")
    
    # 데이터베이스 연결 해제
    if db_import_success:
        try:
            await close_db()
            logger.info("✅ 데이터베이스 연결 해제됨")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 해제 실패: {e}")

    # 데모 프로세스 워치독 종료
    try:
        from services.demo_procs import stop_demo_processes
        stop_demo_processes()
        logger.info("✅ 데모 프로세스 워치독 종료됨")
    except Exception as e:
        logger.error(f"❌ 데모 프로세스 워치독 종료 실패: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
