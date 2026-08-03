"""
디스크 모니터링 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
import psutil
import logging
from typing import List

from core.security import get_current_user
from schemas.disk import DiskMetrics

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitor",
    tags=["디스크"],
    dependencies=[Depends(get_current_user)],
)

# ============================================================
# 디스크 엔드포인트 (3번 목표)
# ============================================================

@router.get("/disks", response_model=List[DiskMetrics])
async def get_disk_metrics():
    """
    모든 마운트 경로의 디스크 사용 현황
    - disk_usage() 활용
    """
    try:
        disks = []
        partitions = psutil.disk_partitions(all=False) # 파티션 별 물리 디스크만(가상 장치 무시)

        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "path": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_pct": usage.percent
                })
            except (OSError, PermissionError):
                # 개별 파티션 접근 실패는 건너뛰고 부분 결과를 유지한다(빈 목록은 정상).
                pass

        return disks
    except Exception as e:
        # DATA-01: 전체 수집 실패는 빈 목록으로 숨기지 않고 구조화된 503으로 구분한다.
        logger.warning("disk list collection failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "collection_failed", "resource": "disks"},
        )

@router.get("/disk", response_model=DiskMetrics)
async def get_disk_usage(path: str = "/"):
    """
    특정 경로의 디스크 사용 현황
    - path: 마운트 경로 (기본값: /)
    """
    try:
        usage = psutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "usage_pct": usage.percent
        }
    except Exception as e:
        # DATA-01: 수집 실패를 0값으로 숨기지 않고 구조화된 503으로 구분 가능하게 한다.
        logger.warning("disk usage collection failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "collection_failed", "resource": "disk"},
        )
