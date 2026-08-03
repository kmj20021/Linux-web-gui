"""DATA-01: 수집 실패와 실제 0값의 구분, OS별 psutil 필드 차이, 보존 정책 검증.

실제 시스템 메트릭·운영 DB에는 접근하지 않고 mock/임시 DB만 사용한다.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import psutil
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from core.models import MonitorSnapshot, WebUser
from core.security import get_current_user
from routers import cpu as cpu_router
from routers import disk as disk_router
from routers import memory as memory_router
from routers import network as network_router


def _viewer() -> WebUser:
    return WebUser(
        username="pytest-viewer",
        hashed_password="synthetic-test-hash",
        role="viewer",
        is_active=True,
    )


def _client(router, prefix="/api") -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix=prefix)
    app.dependency_overrides[get_current_user] = _viewer
    return TestClient(app)


# ============================================================
# 실제 0값(200) vs 수집 실패(503) 구분
# ============================================================

def test_cpu_returns_200_with_real_zero_values(monkeypatch):
    """실제로 0인 값은 200으로 반환되어 실패와 구분된다."""
    monkeypatch.setattr(
        cpu_router.psutil, "cpu_percent",
        lambda *a, **k: [0.0, 0.0] if k.get("percpu") else 0.0,
    )
    monkeypatch.setattr(cpu_router.psutil, "cpu_count", lambda logical: 0)
    monkeypatch.setattr(cpu_router.psutil, "getloadavg", lambda: (0.0, 0.0, 0.0))

    response = _client(cpu_router.router).get("/api/monitor/cpu")
    assert response.status_code == 200
    body = response.json()
    assert body["cpu_total"] == 0.0
    assert body["core_count"] == 0


def test_cpu_returns_503_on_collection_failure(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("collector unavailable")

    monkeypatch.setattr(cpu_router.psutil, "cpu_percent", boom)

    response = _client(cpu_router.router).get("/api/monitor/cpu")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail == {"error": "collection_failed", "resource": "cpu"}


def test_memory_returns_503_on_failure(monkeypatch):
    def boom():
        raise RuntimeError("collector unavailable")

    monkeypatch.setattr(memory_router.psutil, "virtual_memory", boom)

    response = _client(memory_router.router).get("/api/monitor/memory")
    assert response.status_code == 503
    assert response.json()["detail"]["resource"] == "memory"


def test_disks_returns_503_on_failure(monkeypatch):
    def boom(all):
        raise RuntimeError("collector unavailable")

    monkeypatch.setattr(disk_router.psutil, "disk_partitions", boom)

    response = _client(disk_router.router).get("/api/monitor/disks")
    assert response.status_code == 503
    assert response.json()["detail"]["resource"] == "disks"


def test_disks_empty_list_is_a_valid_200_result(monkeypatch):
    """파티션이 없으면 빈 목록(200)이며 실패(503)와 구분된다."""
    monkeypatch.setattr(disk_router.psutil, "disk_partitions", lambda all: [])

    response = _client(disk_router.router).get("/api/monitor/disks")
    assert response.status_code == 200
    assert response.json() == []


def test_network_interfaces_returns_503_on_failure(monkeypatch):
    def boom():
        raise RuntimeError("collector unavailable")

    # network 라우터는 함수 내부에서 psutil 을 import 하므로 실제 모듈을 패치한다.
    monkeypatch.setattr(psutil, "net_if_addrs", boom)

    response = _client(network_router.router).get("/api/network/interfaces")
    assert response.status_code == 503
    assert response.json()["detail"]["resource"] == "network_interfaces"


# ============================================================
# OS별 psutil 필드 차이(buffers·cached)
# ============================================================

def test_memory_handles_missing_buffers_cached_fields(monkeypatch):
    """Windows svmem 처럼 buffers·cached 가 없어도 실패가 아니라 0으로 처리한다."""
    windows_like_mem = SimpleNamespace(
        total=8 * 1024**3,
        used=4 * 1024**3,
        free=4 * 1024**3,
        percent=50.0,
    )
    monkeypatch.setattr(memory_router.psutil, "virtual_memory", lambda: windows_like_mem)

    response = _client(memory_router.router).get("/api/monitor/memory")
    assert response.status_code == 200
    body = response.json()
    assert body["total_gb"] == 8.0
    assert body["buffers_gb"] == 0.0
    assert body["cached_gb"] == 0.0


def test_memory_reports_linux_buffers_cached(monkeypatch):
    """Linux svmem 의 buffers·cached 는 그대로 반영된다."""
    linux_like_mem = SimpleNamespace(
        total=8 * 1024**3,
        used=4 * 1024**3,
        free=2 * 1024**3,
        buffers=1 * 1024**3,
        cached=1 * 1024**3,
        percent=50.0,
    )
    monkeypatch.setattr(memory_router.psutil, "virtual_memory", lambda: linux_like_mem)

    response = _client(memory_router.router).get("/api/monitor/memory")
    assert response.status_code == 200
    body = response.json()
    assert body["buffers_gb"] == 1.0
    assert body["cached_gb"] == 1.0


# ============================================================
# 보존 정책(DEC-08: 7일, 일괄 SQL DELETE)
# ============================================================

def _snapshot(recorded_at: datetime) -> MonitorSnapshot:
    return MonitorSnapshot(
        cpu_total=0.0,
        cpu_per_core=[],
        core_count=0,
        load_avg=[0.0, 0.0, 0.0],
        mem_total_gb=0.0,
        mem_used_gb=0.0,
        mem_free_gb=0.0,
        mem_buffers_gb=0.0,
        mem_cached_gb=0.0,
        mem_usage_pct=0.0,
        top_processes=[],
        recorded_at=recorded_at,
    )


async def test_retention_deletes_only_rows_older_than_window(db_session):
    from services import scheduler

    now = datetime.now(timezone.utc)
    older_than_window = _snapshot(now - timedelta(days=8))
    just_inside_window = _snapshot(now - timedelta(days=7) + timedelta(minutes=1))
    recent = _snapshot(now - timedelta(days=1))
    db_session.add_all([older_than_window, just_inside_window, recent])
    await db_session.commit()

    deleted = await scheduler.cleanup_old_snapshots(days=7)
    assert deleted == 1

    remaining = (
        await db_session.execute(select(MonitorSnapshot.recorded_at))
    ).scalars().all()
    assert len(remaining) == 2


async def test_retention_default_window_is_seven_days(db_session):
    from services import scheduler

    assert scheduler.SNAPSHOT_RETENTION_DAYS == 7

    now = datetime.now(timezone.utc)
    db_session.add_all([
        _snapshot(now - timedelta(days=8)),
        _snapshot(now - timedelta(days=6)),
    ])
    await db_session.commit()

    deleted = await scheduler.cleanup_old_snapshots()
    assert deleted == 1


async def test_retention_returns_zero_when_nothing_expired(db_session):
    from services import scheduler

    now = datetime.now(timezone.utc)
    db_session.add(_snapshot(now - timedelta(hours=1)))
    await db_session.commit()

    deleted = await scheduler.cleanup_old_snapshots(days=7)
    assert deleted == 0
