"""
모니터링 히스토리 변환 및 집계 엔드포인트
최근 60분 단위 데이터 변환
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.sql import desc
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from core.database import get_db
from core.models import MonitorSnapshot
from schemas.history import (
    SnapshotItem,
    AggregatedSnapshot,
    HistoryResponse,
)

router = APIRouter(prefix="/monitor", tags=["모니터링 히스토리"])

# ============================================================
# GET /monitor/history - 최근 히스토리 조회
# ============================================================

@router.get("/history", response_model=HistoryResponse)
async def get_monitor_history(
    period: str = Query("1hour", description="조회 기간: 1hour, 6hours, 24hours"),
    interval: str = Query("1min", description="집계 간격: 1min, 5min, 60min"),
    db: AsyncSession = Depends(get_db),
):
    """
    모니터링 히스토리 조회 및 집계
    
    기간별 CPU/메모리 평균/최소/최대값 반환
    
    예시:
    - GET /monitor/history?period=1hour&interval=1min
      → 최근 1시간 데이터를 1분 단위로 집계
    
    - GET /monitor/history?period=24hours&interval=60min
      → 최근 24시간 데이터를 60분 단위로 집계
    """
    
    # 기간 계산
    period_map = {
        "1hour": timedelta(hours=1),
        "6hours": timedelta(hours=6),
        "24hours": timedelta(hours=24),
        "7days": timedelta(days=7),
    }
    
    if period not in period_map:
        period = "1hour"
    
    time_delta = period_map[period]
    start_time = datetime.now(timezone.utc) - time_delta
    
    # 데이터베이스에서 해당 기간 데이터 조회
    stmt = select(MonitorSnapshot).where(
        MonitorSnapshot.recorded_at >= start_time
    ).order_by(desc(MonitorSnapshot.recorded_at))
    
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    
    if not snapshots:
        return HistoryResponse(
            period=period,
            total_records=0,
            data=[]
        )
    
    # 시간 단위로 그룹핑 (1분, 5분, 60분 선택)
    grouped_data = {}
    
    for snapshot in snapshots:
        # 시간대 계산 (interval에 따라)
        if interval == "1min":
            timestamp_key = snapshot.recorded_at.strftime("%Y-%m-%d %H:%M")
        elif interval == "5min":
            minute = (snapshot.recorded_at.minute // 5) * 5
            timestamp_key = snapshot.recorded_at.replace(minute=minute, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        else:  # 60min
            timestamp_key = snapshot.recorded_at.strftime("%Y-%m-%d %H:00")
        
        if timestamp_key not in grouped_data:
            grouped_data[timestamp_key] = []
        
        grouped_data[timestamp_key].append(snapshot)
    
    # 집계 데이터 생성
    aggregated_list = []
    
    for timestamp_key in sorted(grouped_data.keys(), reverse=True):
        group = grouped_data[timestamp_key]
        
        # CPU 통계
        cpu_values = [s.cpu_total for s in group]
        cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        cpu_min = min(cpu_values) if cpu_values else 0
        cpu_max = max(cpu_values) if cpu_values else 0
        
        # 메모리 통계
        mem_values = [s.mem_usage_pct for s in group]
        mem_avg = sum(mem_values) / len(mem_values) if mem_values else 0
        mem_min = min(mem_values) if mem_values else 0
        mem_max = max(mem_values) if mem_values else 0
        
        # 마지막 상위 프로세스 (최신 데이터)
        latest_processes = group[0].top_processes if group else []
        
        aggregated = AggregatedSnapshot(
            timestamp_minute=timestamp_key,
            cpu_avg=round(cpu_avg, 2),
            cpu_min=round(cpu_min, 2),
            cpu_max=round(cpu_max, 2),
            mem_avg=round(mem_avg, 2),
            mem_min=round(mem_min, 2),
            mem_max=round(mem_max, 2),
            sample_count=len(group),
            latest_top_processes=latest_processes,
        )
        
        aggregated_list.append(aggregated)
    
    return HistoryResponse(
        period=period,
        total_records=len(snapshots),
        data=aggregated_list,
    )


# ============================================================
# GET /monitor/raw-history - 원본 데이터 조회
# ============================================================

@router.get("/raw-history", response_model=List[SnapshotItem])
async def get_raw_history(
    limit: int = Query(100, ge=1, le=1000, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
    db: AsyncSession = Depends(get_db),
):
    """
    최근 모니터링 스냅샷 원본 데이터 조회 (페이지네이션)
    """
    
    stmt = select(MonitorSnapshot).order_by(
        desc(MonitorSnapshot.recorded_at)
    ).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    
    return [
        SnapshotItem(
            id=s.id,
            cpu_total=s.cpu_total,
            mem_usage_pct=s.mem_usage_pct,
            recorded_at=s.recorded_at.isoformat() if s.recorded_at else None,
        )
        for s in snapshots
    ]


# ============================================================
# GET /monitor/stats - 시간대별 통계
# ============================================================

@router.get("/stats")
async def get_monitor_stats(
    hours: int = Query(24, ge=1, le=168, description="조회 시간 (1-168)"),
    db: AsyncSession = Depends(get_db),
):
    """
    최근 N시간 모니터링 통계
    
    반환 데이터:
    - cpu: {avg, min, max, p50, p95, p99}
    - memory: {avg, min, max, p50, p95, p99}
    - total_records: 수집 데이터 개수
    - time_range: {start, end}
    """
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    stmt = select(MonitorSnapshot).where(
        MonitorSnapshot.recorded_at >= cutoff_time
    )
    
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    
    if not snapshots:
        return {
            "message": "수집된 데이터가 없습니다",
            "total_records": 0,
        }
    
    # CPU 데이터 추출
    cpu_values = sorted([s.cpu_total for s in snapshots])
    mem_values = sorted([s.mem_usage_pct for s in snapshots])
    
    # 백분위수 계산 함수
    def percentile(values, p):
        index = int(len(values) * p / 100)
        return values[min(index, len(values) - 1)]
    
    return {
        "cpu": {
            "avg": round(sum(cpu_values) / len(cpu_values), 2),
            "min": round(min(cpu_values), 2),
            "max": round(max(cpu_values), 2),
            "p50": round(percentile(cpu_values, 50), 2),
            "p95": round(percentile(cpu_values, 95), 2),
            "p99": round(percentile(cpu_values, 99), 2),
        },
        "memory": {
            "avg": round(sum(mem_values) / len(mem_values), 2),
            "min": round(min(mem_values), 2),
            "max": round(max(mem_values), 2),
            "p50": round(percentile(mem_values, 50), 2),
            "p95": round(percentile(mem_values, 95), 2),
            "p99": round(percentile(mem_values, 99), 2),
        },
        "total_records": len(snapshots),
        "time_range": {
            "start": cutoff_time.isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
        },
    }
