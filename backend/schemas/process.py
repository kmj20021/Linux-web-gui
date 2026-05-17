"""
프로세스 관련 DTO 스키마
"""
from pydantic import BaseModel


class ProcessInfo(BaseModel):
    """상위 프로세스 정보"""
    pid: int
    name: str
    cpu_pct: float
    mem_pct: float
