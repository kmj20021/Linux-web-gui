"""
SQLAlchemy ORM 모델
모니터링 스냅샷 데이터 저장
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from sqlalchemy.sql import func
from core.database import Base
from datetime import datetime, timezone


class MonitorSnapshot(Base):
    """
    시스템 모니터링 스냅샷 (1분 단위 저장)
    
    설계서 ERD 기준:
    - cpu_total: 전체 CPU 사용률
    - cpu_per_core: 코어별 CPU 사용률 (JSON)
    - core_count: 총 코어 수
    - load_avg: 부하 평균 (JSON)
    - mem_total_gb: 전체 메모리 GB
    - mem_used_gb: 사용 메모리 GB
    - mem_free_gb: 여유 메모리 GB
    - mem_buffers_gb: 버퍼 메모리 GB
    - mem_cached_gb: 캐시 메모리 GB
    - mem_usage_pct: 메모리 사용률
    - top_processes: 상위 프로세스 (JSON)
    - recorded_at: 기록 시간
    """
    
    __tablename__ = "monitor_snapshots"
    
    # 기본키
    id = Column(Integer, primary_key=True, index=True)
    
    # CPU 메트릭
    cpu_total = Column(Float, nullable=False)
    cpu_per_core = Column(JSON, nullable=False)  # [0.0, 1.5, 2.1, ...] 리스트
    core_count = Column(Integer, nullable=False)
    load_avg = Column(JSON, nullable=False)  # [load_1min, load_5min, load_15min]
    
    # 메모리 메트릭
    mem_total_gb = Column(Float, nullable=False)
    mem_used_gb = Column(Float, nullable=False)
    mem_free_gb = Column(Float, nullable=False)
    mem_buffers_gb = Column(Float, nullable=False)
    mem_cached_gb = Column(Float, nullable=False)
    mem_usage_pct = Column(Float, nullable=False)
    
    # 프로세스 정보 (상위 5개)
    top_processes = Column(JSON, nullable=False)  # [{"pid": ..., "name": ..., "cpu_pct": ..., "mem_pct": ...}, ...]
    
    # 타임스탬프
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(), #파이썬의 시간이 아닌 DB의 현재 시간 사용
        nullable=False,
        index=True  # 조회 성능 개선
    )
    
    def __repr__(self): #출력 형식 지정
        return f"<MonitorSnapshot(id={self.id}, cpu_total={self.cpu_total}, recorded_at={self.recorded_at})>"
    
    def to_dict(self):
        """모델을 딕셔너리로 변환"""
        return {
            "id": self.id,
            "cpu_total": self.cpu_total,
            "cpu_per_core": self.cpu_per_core,
            "core_count": self.core_count,
            "load_avg": self.load_avg,
            "mem_total_gb": self.mem_total_gb,
            "mem_used_gb": self.mem_used_gb,
            "mem_free_gb": self.mem_free_gb,
            "mem_buffers_gb": self.mem_buffers_gb,
            "mem_cached_gb": self.mem_cached_gb,
            "mem_usage_pct": self.mem_usage_pct,
            "top_processes": self.top_processes,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
