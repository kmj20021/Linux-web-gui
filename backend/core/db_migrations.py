"""DB-01: Alembic 기반 스키마 마이그레이션 실행 헬퍼.

앱 시작 시 임의 `ALTER TABLE` 대신 버전 관리된 마이그레이션을 head 까지 적용한다.
실패는 숨기지 않고 호출자에게 전파한다(fail-closed) — 스키마 오류가 있으면 서버가
정상으로 위장하지 않고 시작에 실패해야 한다.
"""
import os

from alembic import command
from alembic.config import Config

# 이 파일은 backend/core/db_migrations.py 이므로 부모의 부모가 backend/ 이다.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ALEMBIC_INI = os.path.join(_BACKEND_DIR, "alembic.ini")
_MIGRATIONS_DIR = os.path.join(_BACKEND_DIR, "migrations")

_DEFAULT_URL = "sqlite+aiosqlite:///./linux_web_gui.db"


def _to_sync_url(database_url: str) -> str:
    """비동기 드라이버 URL 을 동기 드라이버 URL 로 변환한다(마이그레이션은 동기)."""
    return database_url.replace("+aiosqlite", "")


def build_alembic_config(database_url: str | None = None) -> Config:
    """실행 CWD 에 의존하지 않도록 절대 경로로 Alembic 설정을 구성한다."""
    cfg = Config(_ALEMBIC_INI)
    cfg.set_main_option("script_location", _MIGRATIONS_DIR)
    url = database_url or os.getenv("DATABASE_URL", _DEFAULT_URL)
    cfg.set_main_option("sqlalchemy.url", _to_sync_url(url))
    return cfg


def run_migrations(database_url: str | None = None) -> None:
    """스키마를 head 까지 마이그레이션한다. 오류는 전파한다(fail-closed)."""
    command.upgrade(build_alembic_config(database_url), "head")
