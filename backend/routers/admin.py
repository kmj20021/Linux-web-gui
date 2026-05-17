"""
Admin 라우터 (admin role 전용)

- GET    /api/admin/users           : 전체 WebUser 목록 조회
- POST   /api/admin/users           : 신규 계정 생성
- PATCH  /api/admin/users/{user_id} : role / is_active 변경
- DELETE /api/admin/users/{user_id} : 계정 삭제
- GET    /api/admin/audit           : LoginLog 조회 (페이지네이션)

모든 엔드포인트는 admin role 사용자만 접근 가능하다.
"""
import re
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import LoginLog, WebUser
from core.security import get_current_admin, get_password_hash


# username 형식: 영문자/숫자/언더스코어 3~20자 (auth.py 와 동일 규칙)
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# 스키마
# ---------------------------------------------------------------------------
class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[str] = None


class AdminUserCreateRequest(BaseModel):
    username: str = Field(..., description="3~20자, 영문/숫자/언더스코어")
    password: str = Field(..., description="8자 이상")
    role: Literal["admin", "viewer"] = Field(
        default="viewer",
        description="기본값 'viewer'",
    )

    @field_validator("username")
    @classmethod
    def _validate_username(cls, v: str) -> str:
        if not _USERNAME_PATTERN.match(v):
            raise ValueError(
                "username은 3~20자의 영문자/숫자/언더스코어(_)만 사용할 수 있습니다."
            )
        return v

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password는 최소 8자 이상이어야 합니다.")
        return v


class AdminUserUpdateRequest(BaseModel):
    role: Optional[Literal["admin", "viewer"]] = None
    is_active: Optional[bool] = None


class AdminUserDeleteResponse(BaseModel):
    message: str
    user_id: int


class LoginLogOut(BaseModel):
    id: int
    username: str
    role: str
    ip_address: Optional[str] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------
def _to_user_out(user: WebUser) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _to_log_out(log: LoginLog) -> LoginLogOut:
    return LoginLogOut(
        id=log.id,
        username=log.username,
        role=log.role,
        ip_address=log.ip_address,
        created_at=log.created_at.isoformat() if log.created_at else None,
    )


async def _count_active_admins(db: AsyncSession) -> int:
    """현재 활성 admin 수를 반환."""
    result = await db.execute(
        select(func.count())
        .select_from(WebUser)
        .where(WebUser.role == "admin", WebUser.is_active.is_(True))
    )
    return int(result.scalar_one())


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------
@router.get("/users", response_model=List[AdminUserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_admin: WebUser = Depends(get_current_admin),
):
    """
    WebUser 목록 반환.
    - 본인 계정 (username == current_admin.username) +
      본인이 생성한 계정 (created_by == current_admin.username) 만 반환한다.
    """
    result = await db.execute(
        select(WebUser)
        .where(
            or_(
                WebUser.username == current_admin.username,
                WebUser.created_by == current_admin.username,
            )
        )
        .order_by(WebUser.id.asc())
    )
    users = result.scalars().all()
    return [_to_user_out(u) for u in users]


@router.post(
    "/users",
    response_model=AdminUserOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    request: AdminUserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: WebUser = Depends(get_current_admin),
):
    """신규 계정 생성. role 기본값은 'viewer'. created_by 에 생성자 username 저장."""
    # username 중복 확인
    result = await db.execute(
        select(WebUser).where(WebUser.username == request.username)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 사용자명입니다.",
        )

    new_user = WebUser(
        username=request.username,
        hashed_password=get_password_hash(request.password),
        role=request.role,
        is_active=True,
        created_by=current_admin.username,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return _to_user_out(new_user)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int,
    request: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: WebUser = Depends(get_current_admin),
):
    """role 또는 is_active 변경. 자기 자신은 변경 금지."""
    if request.role is None and request.is_active is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="변경할 필드가 없습니다.",
        )

    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신의 계정은 변경할 수 없습니다.",
        )

    result = await db.execute(select(WebUser).where(WebUser.id == user_id))
    target: Optional[WebUser] = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    # 마지막 활성 admin 보호: 마지막 admin 을 viewer 로 강등하거나 비활성화 금지
    becoming_non_admin = request.role is not None and request.role != "admin"
    becoming_inactive = request.is_active is False
    if target.role == "admin" and target.is_active and (
        becoming_non_admin or becoming_inactive
    ):
        active_admins = await _count_active_admins(db)
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="마지막 admin 계정은 강등하거나 비활성화할 수 없습니다.",
            )

    if request.role is not None:
        target.role = request.role
    if request.is_active is not None:
        target.is_active = request.is_active

    await db.commit()
    await db.refresh(target)
    return _to_user_out(target)


@router.delete("/users/{user_id}", response_model=AdminUserDeleteResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: WebUser = Depends(get_current_admin),
):
    """계정 삭제. 자기 자신 / 마지막 admin 삭제 금지."""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신의 계정은 삭제할 수 없습니다.",
        )

    result = await db.execute(select(WebUser).where(WebUser.id == user_id))
    target: Optional[WebUser] = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    # 마지막 활성 admin 삭제 금지
    if target.role == "admin" and target.is_active:
        active_admins = await _count_active_admins(db)
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="마지막 admin 계정은 삭제할 수 없습니다.",
            )

    await db.delete(target)
    await db.commit()

    return AdminUserDeleteResponse(
        message="계정이 삭제되었습니다.",
        user_id=user_id,
    )


@router.get("/audit", response_model=List[LoginLogOut])
async def list_audit_logs(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터)"),
    limit: int = Query(50, ge=1, le=500, description="페이지당 개수"),
    db: AsyncSession = Depends(get_db),
    _admin: WebUser = Depends(get_current_admin),
):
    """LoginLog 목록을 최신순으로 페이지네이션 반환."""
    offset = (page - 1) * limit
    result = await db.execute(
        select(LoginLog)
        .order_by(LoginLog.created_at.desc(), LoginLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = result.scalars().all()
    return [_to_log_out(log) for log in logs]
