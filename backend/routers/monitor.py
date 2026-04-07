"""
모니터링 엔드포인트
CPU·메모리·디스크·네트워크 실시간 조회
"""
from fastapi import APIRouter
from pydantic import BaseModel
import psutil
from typing import List, Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/monitor", tags=["모니터링"])

# ============================================================
# 데이터 모델 (Pydantic BaseModel)
# ============================================================

class CPUMetrics(BaseModel):
    """CPU 메트릭"""
    cpu_total: float
    cpu_per_core: List[float]
    core_count: int
    load_avg: List[float]
    recorded_at: str

class MemoryMetrics(BaseModel):
    """메모리 메트릭"""
    total_gb: float
    used_gb: float
    free_gb: float
    buffers_gb: float
    cached_gb: float
    usage_pct: float

class DiskMetrics(BaseModel):
    """디스크 메트릭"""
    path: str # 마운트 경로
    total_gb: float
    used_gb: float
    free_gb: float
    usage_pct: float

class NetworkMetrics(BaseModel):
    """네트워크 메트릭"""
    interface: str      # 인터페이스명 (예: eth0, lo)
    bytes_sent: int     # 송신 바이트(보낸 무게)
    bytes_recv: int     # 수신 바이트(받은 무게)
    packets_sent: int   # 송신 패킷 수(보낸 데이터그램 수)
    packets_recv: int   # 수신 패킷 수(받은 데이터그램 수)
    errin: int          # 입력 오류 수
    errout: int         # 출력 오류 수
    dropin: int         # 입력 드롭 수(받은게 너무 많아 거절)
    dropout: int        # 출력 드롭 수(보낸게 너무 많아 거절)

class ProcessInfo(BaseModel):
    """느리게 만드는 상위 프로세스 정보"""
    pid: int
    name: str
    cpu_pct: float
    mem_pct: float

# ============================================================
# CPU 엔드포인트 (1번 목표)
# ============================================================

@router.get("/cpu", response_model=CPUMetrics)
async def get_cpu_metrics():
    """
    CPU 사용률 조회
    - 전체 사용률
    - 코어별 사용률
    - 부하 평균 (1분, 5분, 15분)
    """
    try:
        cpu_total = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        core_count = psutil.cpu_count(logical=False)
        load_avg = list(psutil.getloadavg())
        recorded_at = datetime.now(timezone.utc).isoformat()
        
        return {
            "cpu_total": cpu_total,
            "cpu_per_core": cpu_per_core,
            "core_count": core_count,
            "load_avg": load_avg,
            "recorded_at": recorded_at
        }
    except Exception as e:
        return {
            "cpu_total": 0.0,
            "cpu_per_core": [],
            "core_count": 0,
            "load_avg": [0.0, 0.0, 0.0],
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }

# ============================================================
# 메모리 엔드포인트 (2번 목표)
# ============================================================

@router.get("/memory", response_model=MemoryMetrics)
async def get_memory_metrics():
    """
    메모리 사용량 조회
    - total: 전체 메모리
    - used: 사용 중
    - free: 여유
    - buffers: 버퍼
    - cached: 캐시
    - usage_pct: 사용률 (%)
    """
    try:
        mem = psutil.virtual_memory()
        
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.free / (1024**3), 2),
            "buffers_gb": round(mem.buffers / (1024**3), 2),
            "cached_gb": round(mem.cached / (1024**3), 2),
            "usage_pct": mem.percent
        }
    except Exception:
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "buffers_gb": 0.0,
            "cached_gb": 0.0,
            "usage_pct": 0.0
        }

# ============================================================
# 프로세스 엔드포인트
# ============================================================

@router.get("/processes", response_model=List[ProcessInfo])
async def get_top_processes():
    """CPU/메모리 상위 프로세스 5개 조회"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu_pct": proc.info['cpu_percent'] or 0.0,
                    "mem_pct": proc.info['memory_percent'] or 0.0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return sorted(processes, key=lambda x: x['cpu_pct'], reverse=True)[:5]
    except Exception:
        return []

# ============================================================
# 디스크 엔드포인트 (3번 목표)
# ============================================================

@router.get("/disks", response_model=List[DiskMetrics])
async def get_disk_metrics():
    """
    모든 마운트 경로의 디스크 사용 현황
    - disk_usage() 활용
    """
    try:
        disks = []
        partitions = psutil.disk_partitions(all=False) # 파티션 별 물리 디스크만(가상 장치 무시)
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "path": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_pct": usage.percent
                })
            except (OSError, PermissionError):
                pass
        
        return disks
    except Exception:
        return []

@router.get("/disk", response_model=DiskMetrics)
async def get_disk_usage(path: str = "/"):
    """
    특정 경로의 디스크 사용 현황
    - path: 마운트 경로 (기본값: /)
    """
    try:
        usage = psutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "usage_pct": usage.percent
        }
    except Exception:
        return {
            "path": path,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "usage_pct": 0.0
        }

# ============================================================
# 네트워크 엔드포인트 (3번 목표)
# ============================================================

@router.get("/network", response_model=List[NetworkMetrics])
async def get_network_metrics():
    """
    네트워크 I/O 통계 (모든 인터페이스)
    - net_io_counters() 활용
    """
    try:
        networks = []
        net_io = psutil.net_io_counters(pernic=True)
        
        for iface_name, io_counters in net_io.items():
            networks.append({
                "interface": iface_name,
                "bytes_sent": io_counters.bytes_sent,
                "bytes_recv": io_counters.bytes_recv,
                "packets_sent": io_counters.packets_sent,
                "packets_recv": io_counters.packets_recv,
                "errin": io_counters.errin,
                "errout": io_counters.errout,
                "dropin": io_counters.dropin,
                "dropout": io_counters.dropout
            })
        
        return networks
    except Exception:
        return []

@router.get("/network/{iface_name}", response_model=NetworkMetrics)
async def get_network_interface_metrics(iface_name: str):
    """
    특정 네트워크 인터페이스 I/O 통계
    - iface_name: eth0, wlan0, lo 등
    """
    try:
        net_io = psutil.net_io_counters(pernic=True) #Network Interface Card
        
        if iface_name not in net_io:
            return {
                "interface": iface_name,
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "errin": 0,
                "errout": 0,
                "dropin": 0,
                "dropout": 0
            }
        
        io = net_io[iface_name]
        return {
            "interface": iface_name,
            "bytes_sent": io.bytes_sent,
            "bytes_recv": io.bytes_recv,
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv,
            "errin": io.errin,
            "errout": io.errout,
            "dropin": io.dropin,
            "dropout": io.dropout
        }
    except Exception:
        return {
            "interface": iface_name,
            "bytes_sent": 0,
            "bytes_recv": 0,
            "packets_sent": 0,
            "packets_recv": 0,
            "errin": 0,
            "errout": 0,
            "dropin": 0,
            "dropout": 0
        }
