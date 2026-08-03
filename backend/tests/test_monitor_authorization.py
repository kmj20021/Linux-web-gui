"""Authorization matrix for REST monitoring endpoints."""

from types import SimpleNamespace

import pytest
import psutil
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from core.database import get_db
from core.models import WebUser
from core.security import get_current_admin, get_current_user
from routers import cpu as cpu_router
from routers import disk as disk_router
from routers import history as history_router
from routers import memory as memory_router
from routers import network as network_router
from routers import process as process_router


VIEWER_ENDPOINTS = (
    "/api/monitor/cpu",
    "/api/monitor/memory",
    "/api/monitor/disks",
    "/api/monitor/disk",
    "/api/monitor/processes",
    "/api/monitor/history",
    "/api/monitor/raw-history",
    "/api/monitor/stats",
    "/api/network/interfaces",
    "/api/network/traffic",
    "/api/network/packets",
)


class _EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []


class _FakeSession:
    async def execute(self, _statement):
        return _EmptyResult()


def _user(role: str) -> WebUser:
    return WebUser(
        username=f"pytest-{role}",
        hashed_password="synthetic-test-hash",
        role=role,
        is_active=True,
    )


def _client(current_user=None) -> TestClient:
    app = FastAPI()
    for router in (
        cpu_router.router,
        memory_router.router,
        disk_router.router,
        history_router.router,
        network_router.router,
        process_router.router,
    ):
        app.include_router(router, prefix="/api")

    async def fake_db():
        yield _FakeSession()

    app.dependency_overrides[get_db] = fake_db
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


@pytest.fixture(autouse=True)
def mocked_monitor_sources(monkeypatch):
    """Keep authorization tests isolated from host metrics and databases."""
    monkeypatch.setattr(
        cpu_router.psutil,
        "cpu_percent",
        lambda *args, **kwargs: [12.5, 25.0] if kwargs.get("percpu") else 18.75,
    )
    monkeypatch.setattr(cpu_router.psutil, "cpu_count", lambda logical: 2)
    monkeypatch.setattr(cpu_router.psutil, "getloadavg", lambda: (0.1, 0.2, 0.3))

    memory = SimpleNamespace(
        total=8 * 1024**3,
        used=4 * 1024**3,
        free=2 * 1024**3,
        buffers=1 * 1024**3,
        cached=1 * 1024**3,
        percent=50.0,
    )
    monkeypatch.setattr(memory_router.psutil, "virtual_memory", lambda: memory)

    partition = SimpleNamespace(mountpoint="/synthetic")
    usage = SimpleNamespace(
        total=10 * 1024**3,
        used=5 * 1024**3,
        free=5 * 1024**3,
        percent=50.0,
    )
    monkeypatch.setattr(
        disk_router.psutil,
        "disk_partitions",
        lambda all: [partition],
    )
    monkeypatch.setattr(disk_router.psutil, "disk_usage", lambda _path: usage)

    fake_process = SimpleNamespace(
        info={
            "pid": 4242,
            "name": "synthetic-process",
            "cpu_percent": 1.0,
            "memory_percent": 2.0,
        }
    )
    monkeypatch.setattr(
        process_router.psutil,
        "process_iter",
        lambda _attrs: [fake_process],
    )

    monkeypatch.setattr(network_router.time, "time", lambda: 1_000.0)
    monkeypatch.setattr(psutil, "net_if_addrs", lambda: {})
    monkeypatch.setattr(psutil, "net_io_counters", lambda pernic: {})
    monkeypatch.setattr(
        psutil,
        "net_connections",
        lambda kind: [],
    )


@pytest.mark.parametrize("path", VIEWER_ENDPOINTS)
def test_monitor_endpoint_authorization_matrix(path):
    assert _client().get(path).status_code == status.HTTP_401_UNAUTHORIZED
    assert _client(_user("viewer")).get(path).status_code == status.HTTP_200_OK
    assert _client(_user("admin")).get(path).status_code == status.HTTP_200_OK


def test_network_connections_authorization_matrix():
    path = "/api/network/connections"

    assert _client().get(path).status_code == status.HTTP_401_UNAUTHORIZED
    assert _client(_user("viewer")).get(path).status_code == status.HTTP_403_FORBIDDEN
    assert _client(_user("admin")).get(path).status_code == status.HTTP_200_OK


def test_monitor_routes_use_server_authorization_dependencies():
    general_routers = (
        cpu_router.router,
        memory_router.router,
        disk_router.router,
        history_router.router,
        network_router.router,
        process_router.router,
    )
    for router in general_routers:
        for route in router.routes:
            assert any(
                dependency.call is get_current_user
                for dependency in route.dependant.dependencies
            )

    connections_route = next(
        route
        for route in network_router.router.routes
        if route.path.endswith("/connections")
    )
    assert any(
        dependency.call is get_current_admin
        for dependency in connections_route.dependant.dependencies
    )
