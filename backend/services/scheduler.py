"""
APScheduler를 이용한 백그라운드 태스크
1분 간격 모니터링 스냅샷 저장
"""
import asyncio
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import psutil

from core.database import AsyncSessionLocal
from core.models import MonitorSnapshot
from routers.websocket import collect_metrics

logger = logging.getLogger(__name__)

# 전역 스케줄러
scheduler = AsyncIOScheduler()


async def save_monitor_snapshot():
    """
    현재 모니터링 메트릭을 수집하여 데이터베이스에 저장
    1분마다 호출됨
    """
    try:
        # 메트릭 수집
        metrics = await collect_metrics()
        
        # 데이터베이스 세션 생성
        async with AsyncSessionLocal() as session:
            # MonitorSnapshot 레코드 생성
            snapshot = MonitorSnapshot(
                cpu_total=metrics.cpu.total,
                cpu_per_core=metrics.cpu.per_core,
                core_count=metrics.cpu.core_count,
                load_avg=metrics.cpu.load_avg,
                mem_total_gb=metrics.memory.total_gb,
                mem_used_gb=metrics.memory.used_gb,
                mem_free_gb=metrics.memory.free_gb,
                mem_buffers_gb=metrics.memory.buffers_gb,
                mem_cached_gb=metrics.memory.cached_gb,
                mem_usage_pct=metrics.memory.usage_pct,
                top_processes=[p.dict() for p in metrics.top_processes],
                recorded_at=datetime.now(timezone.utc),
            )
            
            # 저장
            session.add(snapshot)
            await session.commit()
            
            logger.info(f"✅ 모니터링 스냅샷 저장됨: CPU={metrics.cpu.total:.1f}%, Memory={metrics.memory.usage_pct:.1f}%")
            
    except Exception as e:
        logger.error(f"❌ 스냅샷 저장 실패: {type(e).__name__}: {e}")


def start_scheduler():
    """스케줄러 시작"""
    if scheduler.running:
        logger.warning("⚠️  스케줄러가 이미 실행 중입니다")
        return
    
    # 1분 간격 작업 추가
    scheduler.add_job(
        save_monitor_snapshot,
        'interval',
        minutes=1,
        id='monitor_snapshot_job',
        name='Save monitor snapshot every minute',
        misfire_grace_time=10,
        coalesce=True,  # 여러 실행이 중첩되면 하나만 실행
    )
    
    # 스케줄러 시작
    scheduler.start()
    logger.info("🚀 모니터링 스케줄러 시작됨 (1분 간격)")


def stop_scheduler():
    """스케줄러 중지"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 모니터링 스케줄러 중지됨")


async def cleanup_old_snapshots(days=7):
    """
    오래된 스냅샷 삭제 (옵션)
    기본값: 7일 이상된 데이터 삭제
    """
    from datetime import timedelta
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        async with AsyncSessionLocal() as session:
            stmt = select(MonitorSnapshot).where(
                MonitorSnapshot.recorded_at < cutoff_date
            )
            result = await session.execute(stmt)
            old_snapshots = result.scalars().all()
            
            for snapshot in old_snapshots:
                await session.delete(snapshot)
            
            await session.commit()
            logger.info(f"🗑️  {len(old_snapshots)}개의 오래된 스냅샷 삭제됨")
            
    except Exception as e:
        logger.error(f"스냅샷 정리 실패: {e}")
