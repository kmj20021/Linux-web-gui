"""
메모리 모니터링 엔드포인트
"""
from fastapi import APIRouter
import psutil

from schemas.memory import MemoryMetrics

router = APIRouter(prefix="/monitor", tags=["메모리"])

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

        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.free / (1024**3), 2),
            "buffers_gb": round(mem.buffers / (1024**3), 2),
            "cached_gb": round(mem.cached / (1024**3), 2),
            "usage_pct": mem.percent
        }
    except Exception:
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "buffers_gb": 0.0,
            "cached_gb": 0.0,
            "usage_pct": 0.0
        }
