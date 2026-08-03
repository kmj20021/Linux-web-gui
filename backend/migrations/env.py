"""Alembic 마이그레이션 환경 (DB-01).

앱은 비동기 드라이버(sqlite+aiosqlite)를 쓰지만 마이그레이션은 동기로 실행한다.
DATABASE_URL(또는 config 의 sqlalchemy.url)을 동기 드라이버로 변환해 사용한다.
실제 스키마는 손으로 작성한 versions/ 리비전으로 관리하므로 autogenerate 용
target_metadata 는 두지 않는다.
"""
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

target_metadata = None


def _resolve_sync_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        url = os.getenv("DATABASE_URL", "sqlite:///./linux_web_gui.db")
    # 비동기 드라이버를 동기 드라이버로 변환 (마이그레이션은 동기 실행).
    return url.replace("+aiosqlite", "")


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": _resolve_sync_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite 의 ALTER 제약을 batch 모드로 우회한다.
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
