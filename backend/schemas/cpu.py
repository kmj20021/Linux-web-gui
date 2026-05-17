"""
CPU 관련 DTO 스키마
"""
from pydantic import BaseModel
from typing import List


class CPUMetrics(BaseModel):
    """CPU 메트릭"""
    cpu_total: float
    cpu_per_core: List[float]
    core_count: int
    load_avg: List[float]
    recorded_at: str
