"""DB-01: Alembic 스키마 버전 관리 검증.

모든 검증은 임시 DB 파일에서만 수행한다. 저장소에 추적된 실제 SQLite 파일
(`./linux_web_gui.db`, `../data/linux_web_gui.db`)은 절대 읽거나 변경하지 않는다.
합성 데이터만 사용한다.
"""

import sqlite3
from pathlib import Path

import pytest

from core.db_migrations import run_migrations


def _columns(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _tables(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        conn.close()


def _alembic_version(db_path: str) -> str | None:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchall()
        if not rows:
            return None
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return version[0] if version else None
    finally:
        conn.close()


def test_upgrade_empty_db_creates_current_schema(tmp_path: Path):
    """빈 DB에 upgrade하면 현재 스키마 3개 테이블과 created_by가 생성된다."""
    db_path = tmp_path / "empty.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    run_migrations(url)

    tables = _tables(str(db_path))
    assert {"monitor_snapshots", "web_users", "login_logs"} <= tables
    assert "created_by" in _columns(str(db_path), "web_users")
    assert "username" in _columns(str(db_path), "web_users")
    assert _alembic_version(str(db_path)) is not None


def test_upgrade_legacy_db_adds_created_by_and_preserves_data(tmp_path: Path):
    """created_by 컬럼이 없는 구 DB를 upgrade하면 컬럼을 추가하고 데이터를 보존한다."""
    db_path = tmp_path / "legacy.db"

    # 구 스키마: web_users에 created_by가 없다(과거 ad-hoc ALTER 이전 상태).
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE web_users (
                id INTEGER PRIMARY KEY,
                username VARCHAR(64) NOT NULL UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(16) NOT NULL DEFAULT 'viewer',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "INSERT INTO web_users (username, hashed_password, role) "
            "VALUES ('synthetic-user', 'synthetic-hash', 'admin')"
        )
        conn.commit()
    finally:
        conn.close()

    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    run_migrations(url)

    assert "created_by" in _columns(str(db_path), "web_users")

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT username, role, created_by FROM web_users WHERE username='synthetic-user'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "synthetic-user"
    assert row[1] == "admin"
    assert row[2] is None  # 기존 행의 새 컬럼은 NULL로 보존


def test_upgrade_is_idempotent_when_already_at_head(tmp_path: Path):
    """이미 최신인 DB에 다시 upgrade해도 오류 없이 no-op이다."""
    db_path = tmp_path / "idempotent.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    run_migrations(url)
    first = _alembic_version(str(db_path))
    # 두 번째 실행은 head에서 멱등적으로 성공해야 한다.
    run_migrations(url)
    second = _alembic_version(str(db_path))

    assert first is not None
    assert first == second
    assert "created_by" in _columns(str(db_path), "web_users")


def test_startup_has_no_adhoc_alter_table():
    """앱 시작 경로에 임의 ALTER TABLE 마이그레이션이 남아 있지 않다."""
    main_src = (Path(__file__).resolve().parents[1] / "main.py").read_text(
        encoding="utf-8"
    )
    assert "ensure_web_users_columns" not in main_src
    # 실행되는 ad-hoc DDL 조각이 남아 있지 않은지 확인한다(설명 주석의 단어는 무시).
    assert "ADD COLUMN" not in main_src
    assert 'text("ALTER' not in main_src


def test_reverse_rename_script_is_noop(tmp_path: Path):
    """DEC-01(username 유지)에 반대되는 rename 스크립트는 명시적 no-op이다."""
    from migrations import rename_username_to_login_id as legacy

    db_path = tmp_path / "rename.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE web_users (id INTEGER PRIMARY KEY, username VARCHAR(64))"
        )
        conn.commit()
    finally:
        conn.close()

    # 폐기된 스크립트는 실행돼도 컬럼을 rename하지 않아야 한다.
    legacy.migrate_db(str(db_path))

    cols = _columns(str(db_path), "web_users")
    assert "username" in cols
    assert "login_id" not in cols
