"""End-to-end proof of the REST permission matrix in docs/contracts/security-contract.md.

The existing authorization tests override `get_current_user` / `get_current_admin`
with stand-ins, so they prove a route *declares* the right dependency. They cannot
prove the real chain — decode the token, load the user from the database, re-check
`is_active` and the current role — actually denies the caller.

This module removes every override. It builds the real application from `main`,
seeds an isolated in-memory database, logs in through `POST /api/auth/login` to get
genuine tokens, and calls each contract row as unauthenticated, viewer and admin.
That is RELEASE-01 manual check 1 ("미인증·viewer·admin 권한 행렬") and check 4
("비활성화된 사용자의 REST·WebSocket 접근 거부"), automated so it stays true.

No real credentials, database rows or secrets are used: every value below is
synthetic and the database lives only in memory.
"""

import sys
import types

# alembic 은 import 시점에 POSIX 터미널 크기를 조회한다. 아래 stub 이 먼저 설치되면
# alembic 이 자신을 POSIX 환경으로 오인해 import 에 실패하므로, 진짜 플랫폼 분기를
# 마치도록 alembic 을 먼저 import 한다. Linux 에서는 stub 자체가 설치되지 않는다.
import alembic  # noqa: F401

# 셸 라우터는 POSIX 전용 모듈을 import 한다. Windows 개발 환경에서도 main 이 셸
# 라우터를 등록하도록(=행렬에서 조용히 빠지지 않도록) 먼저 stub 한다.
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
import pytest_asyncio  # noqa: E402
from fastapi import status  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from routers import shell as shell_router  # noqa: E402


SAFE_TEST_SECRET = "synthetic-pytest-matrix-value-not-a-real-secret"
SYNTHETIC_PASSWORD = "synthetic-pytest-password"

VIEWER_NAME = "pytest-matrix-viewer"
ADMIN_NAME = "pytest-matrix-admin"
DEACTIVATED_NAME = "pytest-matrix-deactivated"

# 존재할 가능성이 없는 PID. admin 이라도 DEC-03 allowlist 밖이므로 종료되지 않는다.
UNKNOWN_PID = 4_294_967_000

ALLOW = "allow"
NOT_UNAUTHORIZED = "not-401"


class Row:
    """One row of the contract matrix."""

    def __init__(self, feature, method, path, viewer, admin, json=None):
        self.feature = feature
        self.method = method
        self.path = path
        self.viewer = viewer
        self.admin = admin
        self.json = json

    def __repr__(self):
        return f"{self.method} {self.path}"


MATRIX = (
    # 1. CPU·메모리·디스크·프로세스 조회 — 로그인 사용자에게만 제공
    Row("시스템 메트릭", "GET", "/api/monitor/cpu", ALLOW, ALLOW),
    Row("시스템 메트릭", "GET", "/api/monitor/memory", ALLOW, ALLOW),
    Row("시스템 메트릭", "GET", "/api/monitor/disks", ALLOW, ALLOW),
    Row("시스템 메트릭", "GET", "/api/monitor/disk", ALLOW, ALLOW),
    Row("시스템 메트릭", "GET", "/api/monitor/processes", ALLOW, ALLOW),
    # 2. 히스토리 조회 — 원본·집계 모두 같은 인증 기준
    Row("히스토리", "GET", "/api/monitor/history", ALLOW, ALLOW),
    Row("히스토리", "GET", "/api/monitor/raw-history", ALLOW, ALLOW),
    Row("히스토리", "GET", "/api/monitor/stats", ALLOW, ALLOW),
    # 3. 네트워크 인터페이스·트래픽·패킷
    Row("네트워크 조회", "GET", "/api/network/interfaces", ALLOW, ALLOW),
    Row("네트워크 조회", "GET", "/api/network/traffic", ALLOW, ALLOW),
    Row("네트워크 조회", "GET", "/api/network/packets", ALLOW, ALLOW),
    # 4. 네트워크 연결·PID — 연결 식별자와 PID 는 admin 전용 (DEC-07)
    Row("네트워크 연결", "GET", "/api/network/connections", status.HTTP_403_FORBIDDEN, ALLOW),
    # 5. 프로세스 종료 — viewer 는 항상 403, admin 은 DEC-03 범위만
    Row(
        "프로세스 종료",
        "POST",
        f"/api/monitor/processes/{UNKNOWN_PID}/kill",
        status.HTTP_403_FORBIDDEN,
        NOT_UNAUTHORIZED,
    ),
    # 6. 사용자·감사 로그 관리 (DEC-02)
    Row("사용자 관리", "GET", "/api/admin/users", status.HTTP_403_FORBIDDEN, ALLOW),
    Row("감사 로그", "GET", "/api/admin/audit", status.HTTP_403_FORBIDDEN, ALLOW),
    Row(
        "사용자 생성",
        "POST",
        "/api/admin/users",
        status.HTTP_403_FORBIDDEN,
        ALLOW,
        json={
            "username": "pytest-matrix-created",
            "password": SYNTHETIC_PASSWORD,
            "role": "viewer",
        },
    ),
    # 7. 모니터링 ticket 발급 (DEC-04)
    Row("모니터링 ticket", "POST", "/api/auth/ws-tickets/monitor", ALLOW, ALLOW),
    # 8. 셸 ticket 발급 — 셸은 admin 전용
    Row("셸 ticket", "POST", "/api/auth/ws-tickets/shell", status.HTTP_403_FORBIDDEN, ALLOW),
    # 9. 셸 파일 탐색·초기화
    Row("셸 파일 탐색", "GET", "/api/shell/fs", status.HTTP_403_FORBIDDEN, ALLOW),
    Row("셸 초기화", "DELETE", "/api/shell/reset", status.HTTP_403_FORBIDDEN, ALLOW),
    # 10. 셸 세션 목록
    Row("셸 세션 목록", "GET", "/api/shell/sessions", status.HTTP_403_FORBIDDEN, ALLOW),
)


@pytest_asyncio.fixture
async def matrix_env(monkeypatch, tmp_path):
    """Seed synthetic users into an isolated database and hand back real tokens.

    `conftest` already pinned `DATABASE_URL` to an in-memory SQLite database, so
    nothing here can reach a repository-tracked or production file.
    """
    monkeypatch.setenv("SECRET_KEY", SAFE_TEST_SECRET)
    # 셸 초기화가 실제 webterm 홈을 지우지 않도록 임시 경로로 돌린다.
    monkeypatch.setattr(shell_router, "WEBTERM_HOME", tmp_path)
    monkeypatch.setattr(shell_router, "ACTIVE_SESSIONS", {})
    monkeypatch.setattr(shell_router, "USER_LATEST_SESSION", {})

    from core import models  # noqa: F401 - registers every model with Base
    from core.database import AsyncSessionLocal, Base, engine
    from core.models import WebUser
    from core.security import get_password_hash

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    hashed = get_password_hash(SYNTHETIC_PASSWORD)
    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                WebUser(
                    username=VIEWER_NAME,
                    hashed_password=hashed,
                    role="viewer",
                    is_active=True,
                ),
                WebUser(
                    username=ADMIN_NAME,
                    hashed_password=hashed,
                    role="admin",
                    is_active=True,
                ),
                # 토큰 발급 이후 비활성화된 관리자. 실제 위협 시나리오다.
                WebUser(
                    username=DEACTIVATED_NAME,
                    hashed_password=hashed,
                    role="admin",
                    is_active=False,
                ),
            ]
        )
        await session.commit()

    # TestClient 를 컨텍스트 매니저로 쓰지 않으므로 startup 이벤트(도커 조회,
    # 마이그레이션, 스케줄러)는 실행되지 않는다. 라우팅과 의존성은 실제 앱 그대로다.
    client = TestClient(main.app)

    def login(username):
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": SYNTHETIC_PASSWORD},
        )
        assert response.status_code == status.HTTP_200_OK, (
            f"{username} 로그인이 실패했다: {response.status_code}"
        )
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    yield types.SimpleNamespace(
        client=client,
        viewer=login(VIEWER_NAME),
        admin=login(ADMIN_NAME),
    )

    client.close()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _call(env, row, headers=None):
    return env.client.request(
        row.method,
        row.path,
        headers=headers or {},
        json=row.json,
    )


def _assert_matches(response, expectation, row, who):
    if expectation is ALLOW:
        assert response.status_code not in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ), f"{who} 가 {row} 에서 거부됐다 ({response.status_code})"
    elif expectation is NOT_UNAUTHORIZED:
        assert response.status_code != status.HTTP_401_UNAUTHORIZED, (
            f"{who} 가 {row} 에서 인증 실패로 처리됐다"
        )
    else:
        assert response.status_code == expectation, (
            f"{who} 가 {row} 에서 {expectation} 이어야 하는데 {response.status_code} 였다"
        )


@pytest.mark.parametrize("row", MATRIX, ids=repr)
def test_matrix_rejects_unauthenticated(matrix_env, row):
    """모든 보호 자원은 자격 증명 없이 401 이다."""
    response = _call(matrix_env, row)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        f"{row} 가 미인증 요청에 {response.status_code} 를 반환했다"
    )


@pytest.mark.parametrize("row", MATRIX, ids=repr)
def test_matrix_viewer(matrix_env, row):
    """viewer 는 계약이 허용한 행만 사용할 수 있다."""
    response = _call(matrix_env, row, matrix_env.viewer)
    _assert_matches(response, row.viewer, row, "viewer")


@pytest.mark.parametrize("row", MATRIX, ids=repr)
def test_matrix_admin(matrix_env, row):
    """admin 은 계약이 허용한 행에서 인증·인가로 막히지 않는다."""
    response = _call(matrix_env, row, matrix_env.admin)
    _assert_matches(response, row.admin, row, "admin")


@pytest.mark.parametrize("row", MATRIX, ids=repr)
def test_matrix_rejects_user_deactivated_after_token_issue(matrix_env, row):
    """비활성화된 사용자는 토큰이 아직 유효해도 모든 보호 자원에서 401 이다.

    계약 §1: "인증 정보가 없거나 유효하지 않거나 사용자가 비활성화된 경우 401을
    반환한다." 401 이어야 하는 이유는 프런트엔드 규칙과 맞물린다. 같은 문서가
    "401이면 세션을 정리하고 로그인 상태로 전환하고, 403이면 권한 부족으로
    표시한다"고 정하므로, 비활성 사용자에게 403 을 주면 세션이 정리되지 않고
    화면에 남는다.
    """
    from core.security import create_access_token

    # 로그인은 비활성 사용자를 거부하므로, 토큰 발급 뒤 비활성화된 상황을 재현한다.
    token = create_access_token(data={"sub": DEACTIVATED_NAME, "role": "admin"})
    response = _call(matrix_env, row, {"Authorization": f"Bearer {token}"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        f"{row} 가 비활성 사용자에게 {response.status_code} 를 반환했다"
    )


def test_login_is_rejected_for_a_deactivated_user(matrix_env):
    """비활성 사용자는 올바른 비밀번호로도 토큰을 받지 못하고 401 을 받는다."""
    response = matrix_env.client.post(
        "/api/auth/login",
        json={"username": DEACTIVATED_NAME, "password": SYNTHETIC_PASSWORD},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "access_token" not in response.text


def test_login_does_not_reveal_that_an_account_is_deactivated(matrix_env):
    """계정 상태가 로그인 응답으로 새지 않는다.

    비활성 계정에만 다른 상태 코드나 문구를 주면, 올바른 비밀번호를 가진 공격자가
    "이 자격 증명은 유효하지만 계정이 잠겼다"는 사실을 확인할 수 있다. 잘못된
    비밀번호와 구분되지 않아야 한다.
    """
    deactivated = matrix_env.client.post(
        "/api/auth/login",
        json={"username": DEACTIVATED_NAME, "password": SYNTHETIC_PASSWORD},
    )
    wrong_password = matrix_env.client.post(
        "/api/auth/login",
        json={"username": VIEWER_NAME, "password": "synthetic-wrong-password"},
    )

    assert deactivated.status_code == wrong_password.status_code
    assert deactivated.json() == wrong_password.json()
