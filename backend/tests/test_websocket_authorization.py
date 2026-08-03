"""Focused authorization tests for short-lived WebSocket tickets."""
import sys
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
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


def _ticket_client(user=None, admin=None):
    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    if user is not None:
        async def current_user():
            return user
        app.dependency_overrides[auth.get_current_user] = current_user
    if admin is not None:
        async def current_admin():
            if isinstance(admin, Exception):
                raise admin
            return admin
        app.dependency_overrides[auth.get_current_admin] = current_admin
    return TestClient(app)


def test_ticket_endpoints_enforce_roles_and_no_store():
    assert _ticket_client().post("/api/auth/ws-tickets/monitor").status_code == 401
    viewer = _user()
    monitor = _ticket_client(user=viewer).post("/api/auth/ws-tickets/monitor")
    assert monitor.status_code == 200
    assert monitor.headers["cache-control"] == "no-store"
    assert monitor.json()["expires_in_seconds"] == 60
    assert monitor.json()["ticket"]

    forbidden = HTTPException(status_code=403, detail="Admin privileges required")
    assert _ticket_client(user=viewer, admin=forbidden).post(
        "/api/auth/ws-tickets/shell"
    ).status_code == 403
    shell_response = _ticket_client(user=_user("admin"), admin=_user("admin")).post(
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
async def test_shell_rechecks_current_admin_role_and_rejects_url_credentials(monkeypatch):
    query_ws = _WebSocket(b"token=synthetic-sensitive-value")
    await shell.websocket_shell(query_ws)
    assert query_ws.close_code == 4001

    role_changed_ws = _WebSocket()
    monkeypatch.setattr(shell, "AsyncSessionLocal", lambda: _Session(_user("viewer")))
    monkeypatch.setattr(shell, "consume_ws_ticket", lambda *_args: _value("test_user"))
    await shell.websocket_shell(role_changed_ws)
    assert role_changed_ws.accepted
    assert role_changed_ws.close_code == 4003


async def _value(value):
    return value
