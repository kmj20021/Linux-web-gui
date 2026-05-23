from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict
import time
import threading

router = APIRouter(prefix="/network", tags=["network"])


# -----------------------------------------------------------------------------
# 트래픽 속도 계산을 위한 모듈 전역 캐시
# 인터페이스별 직전 측정값(bytes_sent, bytes_recv, timestamp)을 저장한다.
# 동시 요청에서의 race condition을 막기 위해 lock으로 보호한다.
# -----------------------------------------------------------------------------
_traffic_cache: Dict[str, Dict[str, float]] = {}
_traffic_cache_lock = threading.Lock()


class NetworkInterface(BaseModel):
    name: str
    status: str
    ipv4: Optional[str]
    mac: str
    mtu: int


class NetworkTraffic(BaseModel):
    name: str
    bytes_sent: int
    bytes_recv: int
    bytes_sent_rate: float  # KB/s
    bytes_recv_rate: float  # KB/s


class NetworkPackets(BaseModel):
    name: str
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int


class NetworkConnection(BaseModel):
    proto: str
    local_ip: Optional[str]
    local_port: Optional[int]
    remote_ip: Optional[str]
    remote_port: Optional[int]
    status: str
    pid: Optional[int]
    process_name: Optional[str]


@router.get("/interfaces", response_model=List[NetworkInterface])
async def get_network_interfaces():
    """네트워크 인터페이스 목록 조회"""
    import psutil
    try:
        interfaces = []
        for iface_name, addrs in psutil.net_if_addrs().items():
            ipv4 = None
            mac = None
            for addr in addrs:
                # addr.family는 socket.AddressFamily Enum.
                # str(addr.family)는 '2'와 같은 정수 문자열을 반환하는 경우가 있어
                # 안정적인 비교를 위해 family.name 으로 비교한다.
                # - Linux: IPv4=AF_INET, MAC=AF_PACKET
                # - macOS/BSD: MAC=AF_LINK
                family_name = addr.family.name
                if family_name == 'AF_INET':
                    ipv4 = addr.address
                elif family_name in ('AF_PACKET', 'AF_LINK'):
                    mac = addr.address

            stats = psutil.net_if_stats().get(iface_name)
            if stats:
                interfaces.append({
                    "name": iface_name,
                    "status": "up" if stats.isup else "down",
                    "ipv4": ipv4,
                    "mac": mac or "N/A",
                    "mtu": stats.mtu  # MTU는 인터페이스의 최대 전송 단위로, 네트워크 패킷의 최대 크기를 나타냄
                })
        return interfaces
    except Exception:
        return []


@router.get("/traffic", response_model=List[NetworkTraffic])
async def get_network_traffic():
    """
    실시간 네트워크 트래픽 조회.
    - 각 인터페이스별 누적 송수신 바이트와 직전 호출 대비 평균 KB/s 속도를 반환.
    - 최초 호출 시 이전 측정값이 없으므로 속도는 0.0으로 반환된다.
    """
    import psutil
    try:
        now = time.time()
        counters = psutil.net_io_counters(pernic=True)
        result: List[Dict] = []

        with _traffic_cache_lock:
            for iface_name, c in counters.items():
                prev = _traffic_cache.get(iface_name)
                bytes_sent_rate = 0.0
                bytes_recv_rate = 0.0

                if prev is not None:
                    elapsed = now - prev["timestamp"]
                    if elapsed > 0:
                        sent_diff = c.bytes_sent - prev["bytes_sent"]
                        recv_diff = c.bytes_recv - prev["bytes_recv"]
                        # 카운터 리셋(음수)은 0으로 처리
                        if sent_diff < 0:
                            sent_diff = 0
                        if recv_diff < 0:
                            recv_diff = 0
                        # bytes/s -> KB/s
                        bytes_sent_rate = round((sent_diff / elapsed) / 1024.0, 2)
                        bytes_recv_rate = round((recv_diff / elapsed) / 1024.0, 2)

                # 캐시 갱신
                _traffic_cache[iface_name] = {
                    "bytes_sent": c.bytes_sent,
                    "bytes_recv": c.bytes_recv,
                    "timestamp": now,
                }

                result.append({
                    "name": iface_name,
                    "bytes_sent": c.bytes_sent,
                    "bytes_recv": c.bytes_recv,
                    "bytes_sent_rate": bytes_sent_rate,
                    "bytes_recv_rate": bytes_recv_rate,
                })

        return result
    except Exception:
        return []


@router.get("/packets", response_model=List[NetworkPackets])
async def get_network_packets():
    """
    네트워크 패킷 통계 조회.
    - 각 인터페이스별 송수신 패킷 수, 오류 수, 드롭 수를 반환.
    """
    import psutil
    try:
        counters = psutil.net_io_counters(pernic=True)
        result: List[Dict] = []
        for iface_name, c in counters.items():
            result.append({
                "name": iface_name,
                "packets_sent": c.packets_sent,
                "packets_recv": c.packets_recv,
                "errin": c.errin,
                "errout": c.errout,
                "dropin": c.dropin,
                "dropout": c.dropout,
            })
        return result
    except Exception:
        return []


@router.get("/connections", response_model=List[NetworkConnection])
async def get_network_connections():
    """
    현재 시스템의 열린 포트 및 네트워크 연결 목록 조회.
    - psutil.net_connections(kind='inet')로 TCP/UDP 연결을 조회한다.
    - pid가 존재하면 프로세스 이름을 함께 반환(실패 시 None).
    - 로컬 포트 기준 오름차순으로 정렬한다.
    """
    import psutil
    try:
        # 프로세스 이름 캐시 (pid 중복 조회 방지)
        _proc_name_cache: Dict[int, Optional[str]] = {}

        def _get_proc_name(pid: Optional[int]) -> Optional[str]:
            if pid is None:
                return None
            if pid in _proc_name_cache:
                return _proc_name_cache[pid]
            try:
                name = psutil.Process(pid).name()
            except Exception:
                name = None
            _proc_name_cache[pid] = name
            return name

        result: List[Dict] = []
        for c in psutil.net_connections(kind='inet'):
            # 소켓 타입으로 proto 판별 (SOCK_STREAM=tcp, SOCK_DGRAM=udp)
            try:
                proto = "tcp" if c.type.name == "SOCK_STREAM" else "udp"
            except Exception:
                proto = "tcp"

            local_ip = c.laddr.ip if c.laddr else None
            local_port = c.laddr.port if c.laddr else None
            remote_ip = c.raddr.ip if c.raddr else None
            remote_port = c.raddr.port if c.raddr else None

            result.append({
                "proto": proto,
                "local_ip": local_ip,
                "local_port": local_port,
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "status": c.status if c.status else "NONE",
                "pid": c.pid,
                "process_name": _get_proc_name(c.pid),
            })

        # 로컬 포트 기준 오름차순 정렬 (None은 맨 뒤로)
        result.sort(key=lambda x: (x["local_port"] is None, x["local_port"] or 0))
        return result
    except Exception:
        return []
