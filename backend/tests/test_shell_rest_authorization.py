"""Authorization matrix for the shell REST endpoints.

`/api/shell/fs` was already moved onto the DB-backed admin dependency by SHELL-01.
`/api/shell/reset` and `/api/shell/sessions` kept an older signature-only token
check, so a viewer — who may not use the shell at all — reached the reset logic,
and a deactivated user kept access until the token expired. Both contradict
docs/contracts/security-contract.md (row "셸 파일 탐색·초기화" and section 1).
"""

import sys
import types

# 셸 모듈은 POSIX 전용 모듈을 import 한다. Windows 개발 환경에서도 수집되도록 stub 한다.
for _name, _attrs in (
    ("fcntl", {"ioctl": lambda *_args: None}),
    ("termios", {"TIOCSWINSZ": 0x5414}),
    ("tty", {}),
):
    if _name not in sys.modules:
        _module = types.ModuleType(_name)
        for _key, _value in _attrs.items():
            setattr(_module, _key, _value)
        sys.modules[_name] = _module

import pytest  # noqa: E402
from fastapi import FastAPI, status  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core.models import WebUser  # noqa: E402
from core.security import get_current_admin  # noqa: E402
from routers import shell as shell_router  # noqa: E402


SHELL_REST_ENDPOINTS = (
    ("DELETE", "/api/shell/reset"),
    ("GET", "/api/shell/sessions"),
    ("GET", "/api/shell/fs"),
)


def _user(role: str) -> WebUser:
    return WebUser(
        username=f"pytest-{role}",
        hashed_password="synthetic-test-hash",
        role=role,
        is_active=True,
    )


class _Denied(Exception):
    """Raised by the stand-in admin dependency for viewers and inactive users."""


def _client(current_admin=None) -> TestClient:
    """Build an isolated app.

    `current_admin=None` means the DB-backed dependency rejects the caller, which
    is what happens for missing tokens, deactivated users and viewers.
    """
    app = FastAPI()
    app.include_router(shell_router.router)

    from fastapi import HTTPException

    def admin_dependency():
        if current_admin is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator role required",
            )
        return current_admin

    app.dependency_overrides[get_current_admin] = admin_dependency
    return TestClient(app)


@pytest.fixture(autouse=True)
def isolated_shell_state(tmp_path, monkeypatch):
    """Never touch the real webterm home or any live session."""
    monkeypatch.setattr(shell_router, "WEBTERM_HOME", tmp_path)
    monkeypatch.setattr(shell_router, "ACTIVE_SESSIONS", {})
    monkeypatch.setattr(shell_router, "USER_LATEST_SESSION", {})


@pytest.mark.parametrize("method,path", SHELL_REST_ENDPOINTS)
def test_shell_rest_rejects_unauthenticated(method, path):
    response = _client().request(method, path)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("method,path", SHELL_REST_ENDPOINTS)
def test_shell_rest_rejects_viewer(method, path):
    response = _client(_user("viewer")).request(method, path)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("method,path", SHELL_REST_ENDPOINTS)
def test_shell_rest_routes_depend_on_db_backed_admin(method, path):
    """Signature-only token checks must not be reachable on these routes."""
    route = next(
        route
        for route in shell_router.router.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
    )
    assert any(
        dependency.call is get_current_admin
        for dependency in route.dependant.dependencies
    ), f"{method} {path} must use the DB-backed admin dependency"


def test_viewer_reset_does_not_touch_the_home_directory(tmp_path):
    """A rejected reset must not delete or create anything on disk."""
    home = tmp_path / "pytest-viewer"
    home.mkdir()
    marker = home / "keep.txt"
    marker.write_text("synthetic", encoding="utf-8")

    response = _client(_user("viewer")).request("DELETE", "/api/shell/reset")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert marker.exists(), "viewer 요청이 거부됐는데 홈 디렉터리가 변경됐다"
