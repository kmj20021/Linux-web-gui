"""Focused authorization and concurrency coverage for admin user management."""

import asyncio

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from core.database import AsyncSessionLocal, get_db
from core.models import LoginLog, WebUser
from core.security import get_current_admin, get_current_user
from routers import admin as admin_router


def _user(username: str, role: str, *, created_by: str | None = None) -> WebUser:
    return WebUser(
        username=username,
        hashed_password="synthetic-test-fixture-hash",
        role=role,
        is_active=True,
        created_by=created_by,
    )


class _EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []


class _EmptySession:
    async def execute(self, _statement):
        return _EmptyResult()


def _client(current_user: WebUser | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(admin_router.router, prefix="/api")

    async def fake_db():
        yield _EmptySession()

    app.dependency_overrides[get_db] = fake_db
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


@pytest.mark.parametrize("path", ("/api/admin/users", "/api/admin/audit"))
def test_admin_routes_enforce_server_side_authorization(path):
    viewer = _user("synthetic_viewer", "viewer")
    admin = _user("synthetic_admin", "admin")

    assert _client().get(path).status_code == status.HTTP_401_UNAUTHORIZED
    assert _client(viewer).get(path).status_code == status.HTTP_403_FORBIDDEN
    assert _client(admin).get(path).status_code == status.HTTP_200_OK


def test_admin_routes_depend_on_admin_server_dependency():
    for route in admin_router.router.routes:
        assert any(
            dependency.call is get_current_admin
            for dependency in route.dependant.dependencies
        )


@pytest.mark.asyncio
async def test_admins_manage_users_and_audit_globally_regardless_of_creator(db_session):
    first_admin = _user("synthetic_admin_one", "admin", created_by="bootstrap")
    second_admin = _user("synthetic_admin_two", "admin", created_by="unrelated")
    foreign_viewer = _user(
        "synthetic_foreign_viewer", "viewer", created_by=second_admin.username
    )
    foreign_delete = _user(
        "synthetic_foreign_delete", "viewer", created_by=second_admin.username
    )
    db_session.add_all((first_admin, second_admin, foreign_viewer, foreign_delete))
    await db_session.commit()
    for user in (first_admin, second_admin, foreign_viewer, foreign_delete):
        await db_session.refresh(user)

    db_session.add(LoginLog(username="synthetic-event", role="viewer"))
    await db_session.commit()

    users = await admin_router.list_users(db=db_session, current_admin=first_admin)
    assert [user.id for user in users] == sorted(user.id for user in users)
    assert {user.id for user in users} == {
        first_admin.id,
        second_admin.id,
        foreign_viewer.id,
        foreign_delete.id,
    }

    updated = await admin_router.update_user(
        foreign_viewer.id,
        admin_router.AdminUserUpdateRequest(is_active=False),
        db=db_session,
        current_admin=first_admin,
    )
    assert updated.id == foreign_viewer.id
    assert updated.is_active is False

    deleted = await admin_router.delete_user(
        foreign_delete.id,
        db=db_session,
        current_admin=first_admin,
    )
    assert deleted.user_id == foreign_delete.id

    audit = await admin_router.list_audit_logs(
        page=1, limit=50, db=db_session, _admin=first_admin
    )
    assert len(audit) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ("demote", "delete"))
async def test_concurrent_admin_mutations_preserve_an_active_admin(db_session, operation):
    admin_router._admin_mutation_lock = asyncio.Lock()
    first_admin = _user("synthetic_admin_one", "admin")
    second_admin = _user("synthetic_admin_two", "admin")
    db_session.add_all((first_admin, second_admin))
    await db_session.commit()
    await db_session.refresh(first_admin)
    await db_session.refresh(second_admin)

    async def mutate(target_id: int, current_admin: WebUser):
        async with AsyncSessionLocal() as session:
            try:
                if operation == "demote":
                    return await admin_router.update_user(
                        target_id,
                        admin_router.AdminUserUpdateRequest(role="viewer"),
                        db=session,
                        current_admin=current_admin,
                    )
                return await admin_router.delete_user(
                    target_id,
                    db=session,
                    current_admin=current_admin,
                )
            except HTTPException as exc:
                return exc

    results = await asyncio.gather(
        mutate(second_admin.id, first_admin),
        mutate(first_admin.id, second_admin),
    )

    assert any(not isinstance(result, HTTPException) for result in results)
    assert any(
        isinstance(result, HTTPException)
        and result.status_code == status.HTTP_400_BAD_REQUEST
        for result in results
    )

    async with AsyncSessionLocal() as fresh_session:
        active_admin_count = await fresh_session.scalar(
            select(func.count())
            .select_from(WebUser)
            .where(WebUser.role == "admin", WebUser.is_active.is_(True))
        )
    assert active_admin_count >= 1
