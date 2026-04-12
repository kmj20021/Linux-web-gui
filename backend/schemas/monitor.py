"""
모니터링 관련 DTO 스키마
CPU, 메모리, 디스크, 네트워크 메트릭
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


class MemoryMetrics(BaseModel):
    """메모리 메트릭"""
    total_gb: float
    used_gb: float
    free_gb: float
    buffers_gb: float
    cached_gb: float
    usage_pct: float


class DiskMetrics(BaseModel):
    """디스크 메트릭"""
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_pct: float


class NetworkMetrics(BaseModel):
    """네트워크 메트릭"""
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int


class ProcessInfo(BaseModel):
    """상위 프로세스 정보"""
    pid: int
    name: str
    cpu_pct: float
    mem_pct: float
