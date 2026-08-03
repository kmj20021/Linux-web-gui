"""Shared pytest fixtures with an isolated, in-memory SQLite database."""

import os

import pytest
import pytest_asyncio


# core.database creates its engine while it is imported. Set the test URL before
# any application module can be collected so an import can never select a
# repository-tracked SQLite file.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def _isolate_metrics_collector():
    """PERF-01: 전역 메트릭 수집기 싱글턴이 테스트 간에 새지 않도록 초기화한다."""
    yield
    from services.metrics_collector import reset_collector

    reset_collector()


@pytest_asyncio.fixture
async def db_session():
    """Create the application schema and yield a session backed only by memory."""
    from core import models  # noqa: F401 - registers every model with Base
    from core.database import AsyncSessionLocal, Base, engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def web_user(db_session):
    """Persist a non-privileged synthetic user in the isolated test database."""
    from core.models import WebUser

    user = WebUser(
        username="pytest-viewer",
        hashed_password="synthetic-test-fixture-hash",
        role="viewer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
