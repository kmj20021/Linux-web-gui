"""
CPU 모니터링 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
import psutil
import logging
from datetime import datetime, timezone

from core.security import get_current_user
from schemas.cpu import CPUMetrics

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitor",
    tags=["CPU"],
    dependencies=[Depends(get_current_user)],
)

# ============================================================
# CPU 엔드포인트 (1번 목표)
# ============================================================

@router.get("/cpu", response_model=CPUMetrics)
async def get_cpu_metrics():
    """
    CPU 사용률 조회
    - 전체 사용률
    - 코어별 사용률
    - 부하 평균 (1분, 5분, 15분)
    """
    try:
        cpu_total = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        # cpu_count(logical=False)는 일부 플랫폼에서 None을 반환할 수 있다(OS 차이).
        core_count = psutil.cpu_count(logical=False) or 0
        # getloadavg는 Windows에서 psutil이 에뮬레이션하지만 부재 가능성에 대비한다(OS 차이).
        load_avg = list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [0.0, 0.0, 0.0]
        recorded_at = datetime.now(timezone.utc).isoformat()

        return {
            "cpu_total": cpu_total,
            "cpu_per_core": cpu_per_core,
            "core_count": core_count,
            "load_avg": load_avg,
            "recorded_at": recorded_at
        }
    except Exception as e:
        # DATA-01: 수집 실패를 0값으로 숨기지 않고 구조화된 503으로 구분 가능하게 한다.
        logger.warning("cpu metric collection failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "collection_failed", "resource": "cpu"},
        )
