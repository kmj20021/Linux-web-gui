"""
JWT 인증 및 비밀번호 해싱 유틸리티

- JWT access token 생성/검증
- bcrypt 비밀번호 해싱/검증
- FastAPI 의존성으로 사용할 get_current_user 제공
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.models import WebUser


# ---------------------------------------------------------------------------
# 환경변수 / 상수
# ---------------------------------------------------------------------------
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
# Access Token 만료 시간 (분 단위) - 기본 15분
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


# ---------------------------------------------------------------------------
# 비밀번호 해싱 (bcrypt)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """평문 비밀번호를 bcrypt 해시로 변환"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호 비교"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    JWT access token 생성

    :param data: payload에 담을 데이터 (sub, role 등)
    :param expires_delta: 만료 시간 (None이면 기본 15분)
    :return: 인코딩된 JWT 문자열
    """
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    JWT 검증 및 payload 반환

    :param token: JWT 문자열
    :return: payload (dict)
    :raises HTTPException: 유효하지 않은 토큰일 경우 401
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    if payload.get("sub") is None:
        raise credentials_exception

    return payload


# ---------------------------------------------------------------------------
# FastAPI 의존성
# ---------------------------------------------------------------------------
# tokenUrl 은 OpenAPI 문서용이며 실제 라우터 prefix(/api/auth/login)와 일치
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> WebUser:
    """
    Bearer 토큰으로부터 현재 사용자 조회

    - 토큰 검증
    - DB에서 사용자 조회 후 활성 상태 확인
    - 인증 실패 시 401
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    username: Optional[str] = payload.get("sub")
    if username is None:
        raise credentials_exception

    result = await db.execute(select(WebUser).where(WebUser.username == username))
    user: Optional[WebUser] = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def get_current_admin(
    current_user: WebUser = Depends(get_current_user),
) -> WebUser:
    """
    현재 사용자가 admin role 인지 확인하는 의존성

    - admin 이 아니면 HTTP 403 반환
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
