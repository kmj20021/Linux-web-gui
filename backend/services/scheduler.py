"""
APScheduler를 이용한 백그라운드 태스크
1분 간격 모니터링 스냅샷 저장
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from core.models import MonitorSnapshot
from services.metrics_collector import get_collector

logger = logging.getLogger(__name__)

# DEC-08: 원본 스냅샷은 7일 후 삭제한다.
SNAPSHOT_RETENTION_DAYS = 7


async def current_metrics():
    """단일 수집기의 최신 공유 snapshot을 재사용한다(PERF-01).

    아직 snapshot이 없으면(수집기 미기동 등) 1회만 수집한다.
    """
    collector = get_collector()
    latest = collector.get_latest()
    if latest is not None:
        return latest
    return await collector.collect_once()

# 전역 스케줄러
scheduler = AsyncIOScheduler()


async def save_monitor_snapshot():
    """
    현재 모니터링 메트릭을 수집하여 데이터베이스에 저장
    1분마다 호출됨
    """
    try:
        # 단일 수집기의 최신 공유 snapshot 재사용 (PERF-01)
        metrics = await current_metrics()

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

    # DATA-01/DEC-08: 보존 기간(7일)이 지난 스냅샷을 매일 일괄 삭제한다.
    scheduler.add_job(
        cleanup_old_snapshots,
        'interval',
        hours=24,
        id='snapshot_retention_job',
        name='Delete snapshots older than the retention window',
        misfire_grace_time=60,
        coalesce=True,
    )

    # 스케줄러 시작
    scheduler.start()
    logger.info("🚀 모니터링 스케줄러 시작됨 (스냅샷 1분·보존 24시간 간격)")


def stop_scheduler():
    """스케줄러 중지"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 모니터링 스케줄러 중지됨")


async def cleanup_old_snapshots(days: int = SNAPSHOT_RETENTION_DAYS) -> int:
    """보존 기간(기본 7일, DEC-08)보다 오래된 스냅샷을 일괄 삭제한다.

    행을 하나씩 로드/삭제하지 않고 단일 SQL DELETE 로 처리하며 삭제된 행 수를
    반환한다. cutoff(=now-days)와 정확히 같은 시각의 행은 보존한다(strict `<`).
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(MonitorSnapshot).where(
                    MonitorSnapshot.recorded_at < cutoff_date
                )
            )
            await session.commit()
            deleted = result.rowcount or 0
            logger.info("🗑️  retention: deleted %d snapshot(s) older than %d days", deleted, days)
            return deleted

    except Exception as e:
        logger.error("스냅샷 정리 실패: %s", type(e).__name__)
        return 0
