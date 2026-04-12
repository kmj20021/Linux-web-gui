from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/network", tags=["network"])

class NetworkInterface(BaseModel):
    name: str
    status: str
    ipv4: Optional[str]
    mac: str
    mtu: int

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
                if "IPv4" in str(addr.family):
                    ipv4 = addr.address
                elif "MAC" in str(addr.family) or addr.family.name == 'AF_LINK':
                    mac = addr.address
            
            stats = psutil.net_if_stats().get(iface_name)
            if stats:
                interfaces.append({
                    "name": iface_name,
                    "status": "up" if stats.isup else "down",
                    "ipv4": ipv4,
                    "mac": mac or "N/A",
                    "mtu": stats.mtu # MTU는 인터페이스의 최대 전송 단위로, 네트워크 패킷의 최대 크기를 나타냄
                })
        return interfaces
    except Exception:
        return []
