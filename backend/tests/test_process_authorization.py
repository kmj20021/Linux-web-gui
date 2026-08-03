"""Authorization and allowlist coverage for process termination."""

import psutil
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from core.models import WebUser
from core.security import get_current_admin, get_current_user
from routers import process as process_router


def _user(role: str) -> WebUser:
    return WebUser(
        username=f"pytest-{role}",
        hashed_password="synthetic-test-hash",
        role=role,
        is_active=True,
    )


def _client(current_user=None) -> TestClient:
    app = FastAPI()
    app.include_router(process_router.router, prefix="/api")
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


class FakeManagedProcess:
    def __init__(self, pid: int, *, running: bool = True):
        self.pid = pid
        self.running = running

    def poll(self):
        return None if self.running else 0


class FakePsutilProcess:
    def __init__(self, pid: int, *, name: str, parent_pid: int):
        self.pid = pid
        self._name = name
        self._parent_pid = parent_pid
        self.terminated = False
        self.killed = False

    def name(self):
        return self._name

    def ppid(self):
        return self._parent_pid

    def terminate(self):
        self.terminated = True

    def wait(self, timeout):
        return 0

    def kill(self):
        self.killed = True


def test_kill_requires_authentication():
    response = _client().post("/api/monitor/processes/34567/kill")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_viewer_cannot_kill_process():
    response = _client(_user("viewer")).post(
        "/api/monitor/processes/34567/kill"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_kill_managed_demo_child(monkeypatch):
    pid = 34567
    fake_process = FakePsutilProcess(
        pid,
        name="demo-worker",
        parent_pid=process_router.os.getpid(),
    )
    monkeypatch.setattr(
        process_router.demo_procs,
        "_procs",
        {"demo-worker": FakeManagedProcess(pid)},
    )
    monkeypatch.setattr(process_router.psutil, "Process", lambda requested: fake_process)

    response = _client(_user("admin")).post(
        f"/api/monitor/processes/{pid}/kill"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    assert fake_process.terminated is True
    assert fake_process.killed is False


def test_admin_cannot_kill_existing_process_outside_allowlist(monkeypatch):
    pid = 34567
    fake_process = FakePsutilProcess(
        pid,
        name="unrelated-process",
        parent_pid=process_router.os.getpid(),
    )
    monkeypatch.setattr(process_router.demo_procs, "_procs", {})
    monkeypatch.setattr(process_router.psutil, "Process", lambda requested: fake_process)

    response = _client(_user("admin")).post(
        f"/api/monitor/processes/{pid}/kill"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert fake_process.terminated is False


def test_admin_cannot_kill_non_child_even_if_named_and_managed(monkeypatch):
    pid = 34567
    fake_process = FakePsutilProcess(
        pid,
        name="demo-worker",
        parent_pid=process_router.os.getpid() + 100,
    )
    monkeypatch.setattr(
        process_router.demo_procs,
        "_procs",
        {"demo-worker": FakeManagedProcess(pid)},
    )
    monkeypatch.setattr(process_router.psutil, "Process", lambda requested: fake_process)

    response = _client(_user("admin")).post(
        f"/api/monitor/processes/{pid}/kill"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert fake_process.terminated is False


def test_admin_cannot_kill_protected_pid():
    response = _client(_user("admin")).post("/api/monitor/processes/1/kill")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_missing_pid_returns_not_found_for_admin(monkeypatch):
    def missing_process(_pid):
        raise psutil.NoSuchProcess(_pid)

    monkeypatch.setattr(process_router.psutil, "Process", missing_process)

    response = _client(_user("admin")).post(
        "/api/monitor/processes/34567/kill"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_kill_route_depends_on_admin_authorization():
    route = next(
        route
        for route in process_router.router.routes
        if route.path.endswith("/processes/{pid}/kill")
    )

    # 라우터 수준 로그인 요구와 엔드포인트 수준 admin 요구가 모두 걸려 있어야 한다.
    # 선언 순서에는 의존하지 않는다.
    calls = [dependency.call for dependency in route.dependant.dependencies]
    assert get_current_admin in calls
    assert get_current_user in calls
