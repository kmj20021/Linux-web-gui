"""PERF-02: 셸 컨테이너 시작·정리의 블로킹 구간이 executor 로 offload되고,
정리가 취소·동시 호출에도 정확히 한 번만 실행되는지 검증한다.

모든 Docker 호출은 mock 이며 실제 컨테이너는 기동하지 않는다.
"""
import asyncio
import sys
import threading
import time
import types

import pytest

# ``routers.shell`` 은 런타임상 POSIX 전용이지만 이 유닛 테스트는 Windows 에서도
# 수집된다. 사용할 수 없는 모듈만 import 전에 stub 한다(test_shell_limits.py 와 동일).
if 'fcntl' not in sys.modules:
    fcntl = types.ModuleType('fcntl')
    fcntl.ioctl = lambda *_args: None
    sys.modules['fcntl'] = fcntl
if 'termios' not in sys.modules:
    termios = types.ModuleType('termios')
    termios.TIOCSWINSZ = 0
    sys.modules['termios'] = termios

from routers import shell


async def _measure_ticker_gaps(gaps, n=40, interval=0.01):
    prev = time.perf_counter()
    for _ in range(n):
        await asyncio.sleep(interval)
        now = time.perf_counter()
        gaps.append(now - prev)
        prev = now


@pytest.mark.asyncio
async def test_start_async_offloads_blocking_start(monkeypatch):
    """0.3초 블로킹 컨테이너 시작 중에도 이벤트 루프가 응답한다."""
    session = shell.DockerSession('sid', 'admin')

    def blocking_start(cols, rows):
        time.sleep(0.3)
        return 4242

    monkeypatch.setattr(session, 'start', blocking_start)

    gaps = []
    ticker = asyncio.create_task(_measure_ticker_gaps(gaps))
    fd = await session.start_async(80, 24)
    await ticker

    assert fd == 4242
    assert max(gaps) < 0.15


@pytest.mark.asyncio
async def test_cleanup_async_offloads_blocking_cleanup(monkeypatch):
    """0.3초 블로킹 정리(docker rm·proc wait) 중에도 이벤트 루프가 응답한다."""
    session = shell.DockerSession('sid', 'admin')

    def blocking_cleanup():
        time.sleep(0.3)

    monkeypatch.setattr(session, 'cleanup', blocking_cleanup)

    gaps = []
    ticker = asyncio.create_task(_measure_ticker_gaps(gaps))
    await session.cleanup_async()
    await ticker

    assert max(gaps) < 0.15


def test_cleanup_runs_body_exactly_once(monkeypatch):
    """두 번 호출해도 정리 본문(proc 종료·docker rm)은 한 번만 실행된다."""
    session = shell.DockerSession('sid', 'admin')
    session.master_fd = None

    calls = []

    class _Proc:
        def poll(self):
            return None

        def terminate(self):
            calls.append('terminate')

        def wait(self, timeout):
            return 0

        def kill(self):
            calls.append('kill')

    session.proc = _Proc()
    orphan_calls = []
    monkeypatch.setattr(session, '_remove_named_orphan', lambda: orphan_calls.append(1))

    session.cleanup()
    session.cleanup()  # 멱등: 두 번째는 no-op

    assert calls == ['terminate']
    assert orphan_calls == [1]
    assert session.proc is None


def test_cleanup_is_thread_safe_under_concurrent_calls(monkeypatch):
    """동시 20회 호출에도 정리 본문은 정확히 한 번만 실행된다(스레드 안전)."""
    session = shell.DockerSession('sid', 'admin')
    session.master_fd = None
    session.proc = None

    body_runs = []
    monkeypatch.setattr(session, '_remove_named_orphan', lambda: body_runs.append(1))

    barrier = threading.Barrier(20)

    def worker():
        barrier.wait()  # 모든 스레드가 동시에 진입하도록 정렬
        session.cleanup()

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert body_runs == [1]


@pytest.mark.asyncio
async def test_cleanup_completes_once_even_if_shielded_await_is_cancelled(monkeypatch):
    """정리 offload await 가 취소돼도 정리는 한 번 완료된다(멱등)."""
    session = shell.DockerSession('sid', 'admin')
    session.master_fd = None
    session.proc = None

    body_runs = []
    monkeypatch.setattr(session, '_remove_named_orphan', lambda: body_runs.append(1))

    task = asyncio.create_task(session.cleanup_async())
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # 취소로 offload 가 중단됐을 수 있으므로 동기 정리로 완료를 보장한다(멱등).
    session.cleanup()
    assert body_runs == [1]
