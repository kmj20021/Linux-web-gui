"""Authorization matrix for the shell REST endpoints.

OUT_OF_PLAN_CHANGE (2026-08-07): the shell was opened from admin-only to every
authenticated user (admin and viewer). Server-side enforcement moved from
`get_current_admin` to `get_current_user` on all three REST endpoints; the
per-session ownership check (`session.username != username` -> 403) is
unchanged and is what now carries the isolation burden between two different
viewers. Unauthenticated and deactivated callers must still be rejected.
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
from core.security import get_current_user  # noqa: E402
from routers import shell as shell_router  # noqa: E402


SHELL_REST_ENDPOINTS = (
    ("DELETE", "/api/shell/reset"),
    ("GET", "/api/shell/sessions"),
    ("GET", "/api/shell/fs"),
)


def _user(role: str, username: str = None) -> WebUser:
    return WebUser(
        username=username or f"pytest-{role}",
        hashed_password="synthetic-test-hash",
        role=role,
        is_active=True,
    )


def _client(current_user=None) -> TestClient:
    """Build an isolated app.

    `current_user=None` means the DB-backed dependency rejects the caller, which
    is what happens for missing tokens and deactivated users.
    """
    app = FastAPI()
    app.include_router(shell_router.router)

    from fastapi import HTTPException

    def user_dependency():
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        return current_user

    app.dependency_overrides[get_current_user] = user_dependency
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
@pytest.mark.parametrize("role", ("viewer", "admin"))
def test_shell_rest_allows_any_authenticated_role(method, path, role):
    """Both viewer and admin reach the route logic; neither is blocked by role."""
    response = _client(_user(role)).request(method, path)
    assert response.status_code not in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ), f"{role} was blocked at {method} {path} ({response.status_code})"


@pytest.mark.parametrize("method,path", SHELL_REST_ENDPOINTS)
def test_shell_rest_routes_depend_on_db_backed_user(method, path):
    """Signature-only token checks must not be reachable on these routes."""
    route = next(
        route
        for route in shell_router.router.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
    )
    assert any(
        dependency.call is get_current_user
        for dependency in route.dependant.dependencies
    ), f"{method} {path} must use the DB-backed user dependency"


def test_viewer_cannot_reset_another_viewers_home_directory(tmp_path):
    """Reset only ever touches the caller's own home directory."""
    other_home = tmp_path / "pytest-other-viewer"
    other_home.mkdir()
    marker = other_home / "keep.txt"
    marker.write_text("synthetic", encoding="utf-8")

    response = _client(_user("viewer", username="pytest-viewer")).request(
        "DELETE", "/api/shell/reset"
    )

    assert response.status_code == status.HTTP_200_OK
    assert marker.exists(), "다른 사용자의 홈 디렉터리가 영향을 받았다"


def test_unauthenticated_reset_does_not_touch_the_home_directory(tmp_path):
    """A rejected (unauthenticated) reset must not delete or create anything on disk."""
    home = tmp_path / "pytest-viewer"
    home.mkdir()
    marker = home / "keep.txt"
    marker.write_text("synthetic", encoding="utf-8")

    response = _client(None).request("DELETE", "/api/shell/reset")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert marker.exists(), "미인증 요청이 거부됐는데 홈 디렉터리가 변경됐다"
