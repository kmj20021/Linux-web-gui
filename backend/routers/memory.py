"""
메모리 모니터링 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
import psutil
import logging

from core.security import get_current_user
from schemas.memory import MemoryMetrics

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitor",
    tags=["메모리"],
    dependencies=[Depends(get_current_user)],
)

# ============================================================
# 메모리 엔드포인트 (2번 목표)
# ============================================================

@router.get("/memory", response_model=MemoryMetrics)
async def get_memory_metrics():
    """
    메모리 사용량 조회
    - total: 전체 메모리
    - used: 사용 중
    - free: 여유
    - buffers: 버퍼
    - cached: 캐시
    - usage_pct: 사용률 (%)
    """
    try:
        mem = psutil.virtual_memory()

        # buffers·cached는 Linux svmem에만 있고 Windows svmem에는 없다(OS 차이).
        # 필드 부재를 명시적으로 0으로 처리해 수집 실패로 오인하지 않는다.
        buffers = getattr(mem, "buffers", 0)
        cached = getattr(mem, "cached", 0)

        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.free / (1024**3), 2),
            "buffers_gb": round(buffers / (1024**3), 2),
            "cached_gb": round(cached / (1024**3), 2),
            "usage_pct": mem.percent
        }
    except Exception as e:
        # DATA-01: 수집 실패를 0값으로 숨기지 않고 구조화된 503으로 구분 가능하게 한다.
        logger.warning("memory metric collection failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "collection_failed", "resource": "memory"},
        )
