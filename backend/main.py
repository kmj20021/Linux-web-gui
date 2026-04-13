"""
FastAPI 메인 진입점
라즈베리 파이 기반 Linux 웹 GUI 관리 시스템
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

# 로그 설정 (모든 임포트 전에 정의)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 라우터 임포트
try:
    from routers.monitor import router as monitor_router
    from routers.websocket import router as websocket_router
    from routers.history import router as history_router
    from routers.auth import router as auth_router
    logger_import_success = True
except ImportError as e:
    logger_import_success = False
    import traceback
    traceback.print_exc()

# 데이터베이스 및 스케줄러 임포트
try:
    from core.database import init_db, close_db
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
    app.include_router(auth_router)
    app.include_router(monitor_router)
    app.include_router(websocket_router)
    app.include_router(history_router)
    logger.info("✅ auth, monitor, websocket, history 라우터 등록됨")
else:
    logger.warning("⚠️ 라우터 등록 실패")

@app.get("/api/health", tags=["Health"])
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "message": "서버가 정상 작동 중입니다"}

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 이벤트"""
    logger.info("🚀 FastAPI 서버 시작")
    
    # 데이터베이스 초기화 (테이블 생성)
    if db_import_success:
        try:
            await init_db()
            logger.info("✅ 데이터베이스 접속 및 테이블 생성 완료")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
    
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
