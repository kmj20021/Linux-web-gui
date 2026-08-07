"""Focused authorization tests for short-lived WebSocket tickets."""
import sys
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if sys.platform == "win32" and "fcntl" not in sys.modules:
    sys.modules["fcntl"] = ModuleType("fcntl")
if sys.platform == "win32" and "termios" not in sys.modules:
    termios = ModuleType("termios")
    termios.TIOCSWINSZ = 0
    sys.modules["termios"] = termios

from core import security
from core.models import WebUser
from routers import auth, shell, websocket


@pytest.fixture(autouse=True)
def clear_ticket_store():
    security._ws_tickets.clear()


def _user(role="viewer", active=True):
    return SimpleNamespace(username="test_user", role=role, is_active=active)


def _ticket_client(user=None):
    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    if user is not None:
        async def current_user():
            return user
        app.dependency_overrides[auth.get_current_user] = current_user
    return TestClient(app)


def test_ticket_endpoints_enforce_roles_and_no_store():
    assert _ticket_client().post("/api/auth/ws-tickets/monitor").status_code == 401
    viewer = _user()
    monitor = _ticket_client(user=viewer).post("/api/auth/ws-tickets/monitor")
    assert monitor.status_code == 200
    assert monitor.headers["cache-control"] == "no-store"
    assert monitor.json()["expires_in_seconds"] == 60
    assert monitor.json()["ticket"]

    # 셸 ticket 발급은 admin 전용이 아니라 인증된 사용자(admin·viewer) 모두 허용한다
    # (OUT_OF_PLAN_CHANGE 2026-08-07: 셸을 일반 사용자에게 개방).
    assert _ticket_client().post("/api/auth/ws-tickets/shell").status_code == 401
    viewer_shell = _ticket_client(user=viewer).post("/api/auth/ws-tickets/shell")
    assert viewer_shell.status_code == 200
    assert 0 < viewer_shell.json()["expires_in_seconds"] <= 60

    shell_response = _ticket_client(user=_user("admin")).post(
        "/api/auth/ws-tickets/shell"
    )
    assert shell_response.status_code == 200
    assert 0 < shell_response.json()["expires_in_seconds"] <= 60


@pytest.mark.asyncio
async def test_ticket_consume_is_single_use_purpose_bound_and_expiring(monkeypatch):
    ticket, ttl = await security.issue_ws_ticket("test_user", "monitor")
    assert ttl == 60
    assert await security.consume_ws_ticket(ticket, "shell") is None
    assert await security.consume_ws_ticket(ticket, "monitor") is None

    ticket, _ = await security.issue_ws_ticket("test_user", "monitor")
    assert await security.consume_ws_ticket(ticket, "monitor") == "test_user"
    assert await security.consume_ws_ticket(ticket, "monitor") is None

    ticket, _ = await security.issue_ws_ticket("test_user", "monitor")
    monkeypatch.setattr(security.time, "monotonic", lambda: float("inf"))
    assert await security.consume_ws_ticket(ticket, "monitor") is None


class _Result:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class _Session:
    def __init__(self, user):
        self.user = user

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def execute(self, _query):
        return _Result(self.user)


class _WebSocket:
    def __init__(self, query=b"", ticket="synthetic-ticket"):
        self.scope = {"query_string": query}
        self.ticket = ticket
        self.accepted = False
        self.close_code = None
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def receive_json(self):
        return {"type": "authenticate", "ticket": self.ticket}

    async def close(self, code=None, reason=None):
        self.close_code = code

    async def send_json(self, payload):
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_monitor_rechecks_active_user_after_consuming_ticket(monkeypatch):
    ws = _WebSocket()
    monkeypatch.setattr(websocket, "AsyncSessionLocal", lambda: _Session(_user(active=False)))
    monkeypatch.setattr(websocket, "consume_ws_ticket", lambda *_args: _value("test_user"))
    assert not await websocket._authenticate_monitor_ticket(ws)


@pytest.mark.asyncio
async def test_shell_rejects_url_credentials(monkeypatch):
    query_ws = _WebSocket(b"token=synthetic-sensitive-value")
    await shell.websocket_shell(query_ws)
    assert query_ws.close_code == 4001


@pytest.mark.asyncio
async def test_shell_allows_viewer_role_after_reauth(monkeypatch):
    """셸은 admin 전용이 아니므로, 재확인된 role 이 viewer 여도 4003 으로 막지 않는다.

    (OUT_OF_PLAN_CHANGE 2026-08-07: 셸을 일반 사용자에게 개방. 남은 서버 측 강제는
    비활성 사용자 재확인뿐이며, 아래 테스트가 그 경계를 커버한다.)
    """
    viewer_ws = _WebSocket()
    monkeypatch.setattr(shell, "AsyncSessionLocal", lambda: _Session(_user("viewer")))
    monkeypatch.setattr(shell, "consume_ws_ticket", lambda *_args: _value("test_user"))

    async def _fail_start(*_args, **_kwargs):
        raise RuntimeError("no docker in unit test")

    monkeypatch.setattr(shell.DockerSession, "start_async", _fail_start)
    await shell.websocket_shell(viewer_ws)
    assert viewer_ws.accepted
    # role 검사를 통과해 컨테이너 기동까지 도달했고, 기동 실패 경로(1011)로 닫혔다.
    assert viewer_ws.close_code == 1011


@pytest.mark.asyncio
async def test_shell_rechecks_active_status_and_rejects_deactivated_user(monkeypatch):
    deactivated_ws = _WebSocket()
    monkeypatch.setattr(
        shell, "AsyncSessionLocal", lambda: _Session(_user("admin", active=False))
    )
    monkeypatch.setattr(shell, "consume_ws_ticket", lambda *_args: _value("test_user"))
    await shell.websocket_shell(deactivated_ws)
    assert deactivated_ws.accepted
    assert deactivated_ws.close_code == 4003


async def _value(value):
    return value
