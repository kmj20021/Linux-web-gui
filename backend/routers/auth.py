from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    """ID/PW로 로그인, Access Token 발급"""
    if request.username == "admin" and request.password == "password":
        return {
            "access_token": "test_token_123",
            "token_type": "bearer",
            "expires_in": 900,
            "user": {"username": "admin", "role": "admin"}
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout():
    """로그아웃"""
    return {"message": "Logged out"}

@router.get("/me")
async def get_current_user():
    """현재 사용자 정보"""
    return {"username": "admin", "role": "admin", "status": "active"}
