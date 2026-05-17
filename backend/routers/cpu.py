"""
CPU 모니터링 엔드포인트
"""
from fastapi import APIRouter
import psutil
from datetime import datetime, timezone

from schemas.cpu import CPUMetrics

router = APIRouter(prefix="/monitor", tags=["CPU"])

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
        core_count = psutil.cpu_count(logical=False)
        load_avg = list(psutil.getloadavg())
        recorded_at = datetime.now(timezone.utc).isoformat()

        return {
            "cpu_total": cpu_total,
            "cpu_per_core": cpu_per_core,
            "core_count": core_count,
            "load_avg": load_avg,
            "recorded_at": recorded_at
        }
    except Exception as e:
        return {
            "cpu_total": 0.0,
            "cpu_per_core": [],
            "core_count": 0,
            "load_avg": [0.0, 0.0, 0.0],
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
