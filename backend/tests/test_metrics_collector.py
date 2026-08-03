"""PERF-01: 단일 메트릭 수집기와 공유 fan-out 검증.

한 개의 백그라운드 수집기가 주기적으로 immutable snapshot을 만들고, 모든
소비자(WebSocket 연결·스케줄러)가 그 최신 snapshot을 공유한다. 연결 수가 늘어도
수집 횟수는 늘지 않으며, 블로킹 psutil 호출은 executor로 옮겨 이벤트 루프를
막지 않는다.
"""
import asyncio
import time

import pytest

from schemas.websocket import CPUSnapshot, MemorySnapshot, MonitorMessage
from services.metrics_collector import MetricsCollector


def make_snapshot(tag: str = "snap") -> MonitorMessage:
    return MonitorMessage(
        type="monitor.snapshot",
        cpu=CPUSnapshot(total=1.0, per_core=[1.0], core_count=1, load_avg=[0.0, 0.0, 0.0]),
        memory=MemorySnapshot(
            total_gb=1.0, used_gb=0.5, free_gb=0.5,
            buffers_gb=0.0, cached_gb=0.0, usage_pct=50.0,
        ),
        top_processes=[],
        timestamp=tag,
    )


async def test_get_latest_shared_by_many_consumers():
    """50개의 소비자가 한 번의 수집 결과를 그대로 공유한다(재수집 없음)."""
    calls = 0

    async def fake_collect():
        nonlocal calls
        calls += 1
        return make_snapshot(f"snap-{calls}")

    collector = MetricsCollector(fake_collect, interval=3600)
    snapshot = await collector.collect_once()

    # 50개의 소비자가 최신 snapshot을 읽어도 동일 객체를 공유한다.
    assert all(collector.get_latest() is snapshot for _ in range(50))
    assert collector.collection_count == 1
    assert calls == 1


async def test_wait_for_update_broadcasts_single_collection():
    """대기 중인 여러 소비자가 한 번의 수집으로 모두 깨어나 같은 snapshot을 받는다."""
    async def fake_collect():
        return make_snapshot("broadcast")

    collector = MetricsCollector(fake_collect, interval=3600)
    waiters = [asyncio.create_task(collector.wait_for_update()) for _ in range(10)]
    await asyncio.sleep(0.05)  # 모든 대기자가 구독하도록 양보

    snapshot = await collector.collect_once()
    results = await asyncio.gather(*waiters)

    assert all(result is snapshot for result in results)
    assert collector.collection_count == 1


async def test_collection_count_is_time_driven_not_consumer_driven():
    """소비자 수(50)와 무관하게 수집 횟수는 시간(주기)에만 좌우된다."""
    calls = 0

    async def fake_collect():
        nonlocal calls
        calls += 1
        return make_snapshot()

    collector = MetricsCollector(fake_collect, interval=0.02)
    await collector.start()
    try:
        async def consumer():
            for _ in range(5):
                await collector.wait_for_update()

        await asyncio.gather(*[consumer() for _ in range(50)])
    finally:
        await collector.stop()

    # 50 소비자 x 5 읽기 = 250 읽기지만, 수집은 주기 기반이라 훨씬 적다.
    assert collector.collection_count < 50
    assert collector.collection_count >= 1
    assert calls == collector.collection_count


async def test_event_loop_not_blocked_while_collecting():
    """수집이 executor로 offload되면 0.3초 블로킹 중에도 루프가 응답한다."""
    def blocking():
        time.sleep(0.3)
        return make_snapshot()

    async def offloaded_collect():
        return await asyncio.to_thread(blocking)

    collector = MetricsCollector(offloaded_collect, interval=3600)

    gaps = []

    async def ticker():
        prev = time.perf_counter()
        for _ in range(40):
            await asyncio.sleep(0.01)
            now = time.perf_counter()
            gaps.append(now - prev)
            prev = now

    ticker_task = asyncio.create_task(ticker())
    await collector.collect_once()  # 0.3초 블로킹이지만 offload됨
    await ticker_task

    # 루프가 막혔다면 gap 하나가 ~0.3초가 된다. offload면 작게 유지된다.
    assert max(gaps) < 0.15


async def test_real_collect_metrics_offloads_to_thread(monkeypatch):
    """실제 collect_metrics가 블로킹 수집을 executor 스레드로 offload한다.

    타이밍 대신 offload 계약을 직접 검증한다: 블로킹 수집 함수가
    `asyncio.to_thread`로 실행되는지 확인한다(GIL·실제 psutil 부하에 의존하지 않음).
    """
    from routers import websocket as ws

    real_to_thread = asyncio.to_thread
    captured = {}

    async def spy_to_thread(func, *args, **kwargs):
        captured["func"] = func
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(ws.asyncio, "to_thread", spy_to_thread)

    message = await ws.collect_metrics()

    assert captured.get("func") is ws._collect_metrics_blocking
    assert message.type == "monitor.snapshot"


async def test_start_stop_idempotent_and_halts_collection():
    async def fake_collect():
        return make_snapshot()

    collector = MetricsCollector(fake_collect, interval=0.02)
    await collector.start()
    await collector.start()  # 중복 start는 무해
    await asyncio.sleep(0.06)
    await collector.stop()

    count_after_stop = collector.collection_count
    await asyncio.sleep(0.06)
    assert collector.collection_count == count_after_stop  # 중지 후 수집 없음
    assert collector.running is False

    await collector.stop()  # 중복 stop은 무해
    assert collector.running is False


async def test_scheduler_reuses_collector_snapshot(monkeypatch):
    """스케줄러는 수집기의 공유 snapshot을 재사용하고 재수집하지 않는다."""
    from services import scheduler

    sentinel = make_snapshot("shared")

    class FakeCollector:
        def get_latest(self):
            return sentinel

        async def collect_once(self):
            raise AssertionError("최신 snapshot이 있으면 재수집하면 안 된다")

    monkeypatch.setattr(scheduler, "get_collector", lambda: FakeCollector())

    result = await scheduler.current_metrics()
    assert result is sentinel


async def test_scheduler_collects_once_when_no_snapshot(monkeypatch):
    """수집기 snapshot이 아직 없으면 스케줄러가 1회만 수집한다."""
    from services import scheduler

    produced = make_snapshot("first")
    calls = 0

    class FakeCollector:
        def get_latest(self):
            return None

        async def collect_once(self):
            nonlocal calls
            calls += 1
            return produced

    monkeypatch.setattr(scheduler, "get_collector", lambda: FakeCollector())

    result = await scheduler.current_metrics()
    assert result is produced
    assert calls == 1
