"""
메모리 관련 DTO 스키마
"""
from pydantic import BaseModel


class MemoryMetrics(BaseModel):
    """메모리 메트릭"""
    total_gb: float
    used_gb: float
    free_gb: float
    buffers_gb: float
    cached_gb: float
    usage_pct: float
