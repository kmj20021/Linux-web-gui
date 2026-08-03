"""단일 백그라운드 메트릭 수집기와 공유 fan-out (PERF-01).

하나의 백그라운드 태스크가 주기적으로 시스템 메트릭을 수집해 immutable
snapshot 하나를 만든다. 모든 소비자(WebSocket 연결·스케줄러)는 이 최신
snapshot을 공유받아 재사용하므로, 연결 수가 늘어도 수집 횟수는 증가하지 않는다.

블로킹 psutil 호출은 수집 콜러블 안에서 executor로 옮겨(`asyncio.to_thread`)
이벤트 루프를 막지 않는다. 수집기 lifecycle은 애플리케이션 시작·종료 이벤트에서
명시적으로 관리한다.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from schemas.websocket import MonitorMessage

logger = logging.getLogger(__name__)

# WebSocket 브로드캐스트 주기와 동일한 기본 수집 주기(초).
DEFAULT_INTERVAL_SECONDS = 5.0


class MetricsCollector:
    """주기적으로 하나의 snapshot을 만들어 모든 소비자에게 fan-out한다."""

    def __init__(
        self,
        collect: Callable[[], Awaitable[MonitorMessage]],
        interval: float = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        self._collect = collect
        self._interval = float(interval)
        self._latest: Optional[MonitorMessage] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._collection_count = 0
        self._condition = asyncio.Condition()

    @property
    def running(self) -> bool:
        return self._running

    @property
    def collection_count(self) -> int:
        return self._collection_count

    def get_latest(self) -> Optional[MonitorMessage]:
        """가장 최근에 수집된 공유 snapshot(없으면 None)."""
        return self._latest

    async def collect_once(self) -> MonitorMessage:
        """1회 수집하고 최신 snapshot을 교체한 뒤 대기 중인 소비자를 깨운다."""
        snapshot = await self._collect()
        async with self._condition:
            self._latest = snapshot
            self._collection_count += 1
            self._condition.notify_all()
        return snapshot

    async def wait_for_update(self) -> MonitorMessage:
        """다음 수집이 도착할 때까지 기다렸다가 공유 snapshot을 반환한다."""
        async with self._condition:
            await self._condition.wait()
            return self._latest

    async def _run(self) -> None:
        # 첫 snapshot을 즉시 만들어 최초 소비자의 대기 시간을 줄인다.
        try:
            await self.collect_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("초기 메트릭 수집 실패")

        while self._running:
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            if not self._running:
                break
            try:
                await self.collect_once()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("메트릭 수집 주기 실패")

    async def start(self) -> None:
        """백그라운드 수집 루프를 시작한다(중복 호출은 무해)."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """백그라운드 수집 루프를 중지한다(중복 호출은 무해)."""
        if not self._running and self._task is None:
            return
        self._running = False
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ============================================================
# 프로세스 전역 싱글턴
# ============================================================

_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """애플리케이션 전역 수집기 싱글턴을 반환한다.

    실제 수집 함수(`routers.websocket.collect_metrics`)는 순환 임포트를 피하기
    위해 최초 접근 시점에 지연 임포트한다.
    """
    global _collector
    if _collector is None:
        from routers.websocket import collect_metrics

        _collector = MetricsCollector(collect_metrics)
    return _collector


def reset_collector() -> None:
    """전역 수집기 싱글턴을 정리하고 초기화한다(주로 테스트 격리용).

    실행 중인 백그라운드 태스크는 best-effort로 취소한다(await 없이).
    """
    global _collector
    if _collector is not None:
        _collector._running = False
        if _collector._task is not None:
            _collector._task.cancel()
        _collector = None
