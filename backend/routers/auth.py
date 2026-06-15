"""
인증 라우터 (JWT 기반)

- POST /api/auth/login    : 로그인 → access_token 발급
- POST /api/auth/logout   : 로그아웃 (서버는 200 반환, 클라이언트가 토큰 삭제)
- POST /api/auth/register : 회원가입 (기본 role: viewer)
- GET  /api/auth/me       : Bearer 토큰으로 현재 사용자 정보 조회
"""
import re
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.models import LoginLog, WebUser
from core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)


# username 형식: 영문자/숫자/언더스코어 3~20자
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# 스키마
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class MeResponse(BaseModel):
    username: str
    role: str
    is_active: bool


class RegisterRequest(BaseModel):
    username: str = Field(..., description="3~20자, 영문/숫자/언더스코어만 허용")
    password: str = Field(..., description="8자 이상")
    password_confirm: str = Field(..., description="password와 동일해야 함")

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

    @model_validator(mode="after")
    def _validate_password_match(self) -> "RegisterRequest":
        if self.password != self.password_confirm:
            raise ValueError("password와 password_confirm이 일치하지 않습니다.")
        return self


class RegisterResponse(BaseModel):
    message: str
    username: str
    role: str


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    ID/PW 로그인 → JWT access_token 발급
    로그인 성공 시 LoginLog 에 기록한다.
    """
    result = await db.execute(
        select(WebUser).where(WebUser.username == request.username)
    )
    user: Optional[WebUser] = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=expires_delta,
    )

    # 로그인 성공 이벤트 기록
    ip_address: Optional[str] = None
    if http_request.client is not None:
        ip_address = http_request.client.host
    db.add(
        LoginLog(
            username=user.username,
            role=user.role,
            ip_address=ip_address,
        )
    )
    await db.commit()

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
        user=UserInfo(username=user.username, role=user.role),
    )


@router.post("/logout")
async def logout():
    """
    로그아웃
    - 클라이언트가 토큰을 삭제해야 하며, 서버는 200을 반환
    - (서버 측 블랙리스트는 본 작업 범위 외)
    """
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
async def me(current_user: WebUser = Depends(get_current_user)):
    """
    Bearer 토큰으로 현재 사용자 정보 반환
    """
    return MeResponse(
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    회원가입
    - username: 3~20자, 영문/숫자/언더스코어만
    - password: 8자 이상
    - password_confirm: password와 일치해야 함
    - 기본 role: "viewer"
    - is_active: True
    """
    # username 중복 확인
    result = await db.execute(
        select(WebUser).where(WebUser.username == request.username)
    )
    existing_user: Optional[WebUser] = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 사용자명입니다.",
        )

    # 비밀번호 해싱 후 사용자 생성
    new_user = WebUser(
        username=request.username,
        hashed_password=get_password_hash(request.password),
        role="viewer",
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return RegisterResponse(
        message="회원가입이 완료되었습니다.",
        username=new_user.username,
        role=new_user.role,
    )
