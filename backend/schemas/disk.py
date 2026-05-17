"""
디스크 관련 DTO 스키마
"""
from pydantic import BaseModel


class DiskMetrics(BaseModel):
    """디스크 메트릭"""
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_pct: float
