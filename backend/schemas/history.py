"""
히스토리 관련 DTO 스키마
과거 데이터 조회 및 집계 응답
"""
from pydantic import BaseModel
from typing import List


class SnapshotItem(BaseModel):
    """개별 스냅샷 항목"""
    id: int
    cpu_total: float
    mem_usage_pct: float
    recorded_at: str


class AggregatedSnapshot(BaseModel):
    """60분 집계 데이터"""
    timestamp_minute: str  # 예: "2026-04-12 14:00"
    cpu_avg: float  # 평균 CPU
    cpu_min: float  # 최소 CPU
    cpu_max: float  # 최대 CPU
    mem_avg: float  # 평균 메모리
    mem_min: float  # 최소 메모리
    mem_max: float  # 최대 메모리
    sample_count: int  # 수집 샘플 수
    latest_top_processes: List  # 마지막 상위 프로세스


class HistoryResponse(BaseModel):
    """히스토리 응답"""
    period: str  # "1hour", "6hours", "24hours"
    total_records: int
    data: List[AggregatedSnapshot]
