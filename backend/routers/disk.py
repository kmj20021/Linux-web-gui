"""
디스크 모니터링 엔드포인트
"""
from fastapi import APIRouter
import psutil
from typing import List

from schemas.disk import DiskMetrics

router = APIRouter(prefix="/monitor", tags=["디스크"])

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
                pass

        return disks
    except Exception:
        return []

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
    except Exception:
        return {
            "path": path,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "usage_pct": 0.0
        }
