from fastapi import APIRouter
from pydantic import BaseModel
import psutil
from typing import List
from datetime import datetime, timezone

router = APIRouter(prefix="/monitor", tags=["monitor"])

class CPUMetrics(BaseModel):
    cpu_total: float
    cpu_per_core: List[float]
    core_count: int
    recorded_at: str

class MemoryMetrics(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    usage_pct: float

@router.get("/cpu", response_model=CPUMetrics)
async def get_cpu_metrics():
    """CPU 사용률 조회"""
    try:
        cpu_total = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        core_count = psutil.cpu_count(logical=False)
        recorded_at = datetime.now(timezone.utc).isoformat()
        
        return {
            "cpu_total": cpu_total,
            "cpu_per_core": cpu_per_core,
            "core_count": core_count,
            "recorded_at": recorded_at
        }
    except Exception as e:
        return {
            "cpu_total": 0.0,
            "cpu_per_core": [],
            "core_count": 0,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }

@router.get("/memory", response_model=MemoryMetrics)
async def get_memory_metrics():
    """메모리 사용량 조회"""
    try:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.free / (1024**3), 2),
            "usage_pct": mem.percent
        }
    except Exception:
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "usage_pct": 0.0
        }
