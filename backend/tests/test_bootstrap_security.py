"""Security regression coverage for application bootstrap and first admin setup."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select


SAFE_TEST_SECRET = "pytest-only-secret-key-with-at-least-32-characters"


def _disable_unrelated_startup_work(monkeypatch, main):
    docker_calls = []

    def fake_docker_check(*args, **kwargs):
        docker_calls.append((args, kwargs))
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(main.subprocess, "run", fake_docker_check)
    # DB-01: 시작 시 DB 초기화는 Alembic run_migrations 로 대체됐다. 부트스트랩
    # 보안 검사(SECRET_KEY 우선 검증·admin 미생성)만 확인하도록 이를 no-op 처리한다.
    monkeypatch.setattr(main, "run_migrations", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "start_scheduler", lambda: None)

    from services import demo_procs

    monkeypatch.setattr(demo_procs, "start_demo_processes", lambda: None)

    # PERF-01: startup 은 이제 단일 메트릭 수집기를 시작한다. 부트스트랩 보안
    # 검사와 무관하므로 실제 백그라운드 태스크를 만들지 않도록 no-op 처리한다.
    from services import metrics_collector

    class _NoopCollector:
        async def start(self):
            return None

        async def stop(self):
            return None

    monkeypatch.setattr(metrics_collector, "get_collector", lambda: _NoopCollector())
    return docker_calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "secret_key",
    [
        None,
        "your-secret-key-change-in-production",
        "your-secret-key-here",
    ],
)
async def test_startup_rejects_missing_or_placeholder_secret_before_side_effects(
    monkeypatch,
    secret_key,
):
    import main

    if secret_key is None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", secret_key)

    docker_calls = _disable_unrelated_startup_work(monkeypatch, main)
    if hasattr(main, "ensure_default_admin"):
        monkeypatch.setattr(main, "ensure_default_admin", AsyncMock())

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        await main.startup_event()

    assert docker_calls == []


@pytest.mark.asyncio
async def test_startup_fails_closed_on_migration_error(monkeypatch):
    """DB-01: 스키마 마이그레이션 실패를 startup 이 숨기지 않고 그대로 전파한다."""
    import main

    monkeypatch.setenv("SECRET_KEY", SAFE_TEST_SECRET)
    _disable_unrelated_startup_work(monkeypatch, main)

    def boom(*args, **kwargs):
        raise RuntimeError("schema migration failed")

    monkeypatch.setattr(main, "run_migrations", boom)
    if hasattr(main, "ensure_default_admin"):
        monkeypatch.setattr(main, "ensure_default_admin", AsyncMock())

    with pytest.raises(RuntimeError, match="schema migration failed"):
        await main.startup_event()


@pytest.mark.asyncio
async def test_default_startup_does_not_create_an_admin(monkeypatch, db_session):
    import main
    from core.models import WebUser

    monkeypatch.setenv("SECRET_KEY", SAFE_TEST_SECRET)
    _disable_unrelated_startup_work(monkeypatch, main)

    await main.startup_event()

    result = await db_session.execute(
        select(WebUser).where(WebUser.role == "admin")
    )
    assert result.scalar_one_or_none() is None


def test_create_admin_cli_uses_stdin_and_prevents_a_second_admin(tmp_path):
    backend_dir = Path(__file__).parents[1]
    database_path = tmp_path / "bootstrap.db"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    username = "pytest_admin"
    password = "S" * 12 + "7!"
    stdin_payload = f"{username}\n{password}\n{password}\n"

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("SECRET_KEY", None)

    first = subprocess.run(
        [sys.executable, "-m", "cli.create_admin"],
        cwd=backend_dir,
        env=env,
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert first.returncode == 0
    assert password not in first.stdout
    assert password not in first.stderr

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT username, hashed_password, role, is_active "
            "FROM web_users"
        ).fetchone()

    assert row is not None
    assert row[0] == username
    assert row[1] != password
    assert row[2:] == ("admin", 1)

    second_username = "other_admin"
    second_stdin_payload = (
        f"{second_username}\n{password}\n{password}\n"
    )
    second = subprocess.run(
        [sys.executable, "-m", "cli.create_admin"],
        cwd=backend_dir,
        env=env,
        input=second_stdin_payload,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert second.returncode != 0
    assert password not in second.stdout
    assert password not in second.stderr

    with sqlite3.connect(database_path) as connection:
        admin_count = connection.execute(
            "SELECT COUNT(*) FROM web_users WHERE role = 'admin'"
        ).fetchone()[0]

    assert admin_count == 1


def test_create_admin_cli_rejects_command_line_arguments(tmp_path):
    backend_dir = Path(__file__).parents[1]
    database_path = tmp_path / "unused.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = (
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("SECRET_KEY", None)

    result = subprocess.run(
        [sys.executable, "-m", "cli.create_admin", "unexpected-argument"],
        cwd=backend_dir,
        env=env,
        input="",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 2
    assert not database_path.exists()
