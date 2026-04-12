"""
WebSocket 관련 DTO 스키마
실시간 모니터링 메시지 포맷
"""
from pydantic import BaseModel
from typing import List


class CPUSnapshot(BaseModel):
    """CPU 스냅샷"""
    total: float
    per_core: List[float]
    core_count: int
    load_avg: List[float]


class MemorySnapshot(BaseModel):
    """메모리 스냅샷"""
    total_gb: float
    used_gb: float
    free_gb: float
    buffers_gb: float
    cached_gb: float
    usage_pct: float


class ProcessSnapshot(BaseModel):
    """프로세스 정보"""
    pid: int
    name: str
    cpu_pct: float
    mem_pct: float


class MonitorMessage(BaseModel):
    """모니터링 WebSocket 메시지"""
    type: str  # "monitor.snapshot"
    cpu: CPUSnapshot
    memory: MemorySnapshot
    top_processes: List[ProcessSnapshot]
    timestamp: str  # ISO 8601 UTC
