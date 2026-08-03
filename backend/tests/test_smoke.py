"""Minimal application and database smoke coverage."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


def test_database_engine_is_isolated_from_tracked_sqlite_files():
    from core import database

    tracked_databases = {
        (Path(__file__).parents[1] / "linux_web_gui.db").resolve(),
        (Path(__file__).parents[2] / "data" / "linux_web_gui.db").resolve(),
    }

    assert database.DATABASE_URL == "sqlite+aiosqlite:///:memory:"
    assert database.engine.url.database == ":memory:"
    assert all(database.engine.url.database != str(path) for path in tracked_databases)


@pytest.mark.asyncio
async def test_user_fixture_is_persisted_in_temporary_database(db_session, web_user):
    from core.models import WebUser

    result = await db_session.execute(
        select(WebUser).where(WebUser.id == web_user.id)
    )

    assert result.scalar_one() is web_user
    assert web_user.role == "viewer"
    assert web_user.is_active is True


@pytest.mark.asyncio
async def test_health_endpoint_smoke():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
