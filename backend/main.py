"""
FastAPI 메인 진입점
라즈베리 파이 기반 Linux 웹 GUI 관리 시스템
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 라우터 임포트
try:
    from routers.monitor import router as monitor_router
    logger_import_success = True
except ImportError as e:
    logger_import_success = False
    import traceback
    traceback.print_exc()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    app.include_router(monitor_router)
    logger.info("✅ monitor 라우터 등록됨")
else:
    logger.warning("⚠️ monitor 라우터 등록 실패")

@app.get("/api/health", tags=["Health"])
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "message": "서버가 정상 작동 중입니다"}

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 FastAPI 서버 시작")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 FastAPI 서버 종료")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
