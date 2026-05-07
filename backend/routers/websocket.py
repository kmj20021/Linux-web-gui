"""
WebSocket 실시간 모니터링 엔드포인트
CPU·메모리·프로세스 1초 간격 브로드캐스트
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from urllib.parse import parse_qs
from jose import JWTError, jwt
import psutil
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

from schemas.websocket import (
    CPUSnapshot,
    MemorySnapshot,
    ProcessSnapshot,
    MonitorMessage,
)
from core.security import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# ============================================================
# 인증 및 헬퍼 함수
# ============================================================

def verify_token(token: Optional[str]) -> bool:
    """
    JWT 토큰 검증 (WebSocket 전용, bool 반환)

    - token이 None/빈 문자열이면 False
    - core.security 의 SECRET_KEY/ALGORITHM 으로 디코딩
    - payload.sub 가 존재해야 True
    - JWTError(만료, 서명 불일치 등) 발생 시 False
    """
    if not token:
        return False
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub") is not None
    except JWTError:
        return False

async def collect_metrics() -> MonitorMessage:
    """
    현재 시스템 메트릭 수집
    CPU, 메모리, 상위 프로세스 5개
    """
    try:
        # CPU 메트릭
        cpu_total = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(interval=0.05, percpu=True)
        core_count = psutil.cpu_count(logical=False)
        load_avg = list(psutil.getloadavg())
        
        cpu_snapshot = CPUSnapshot(
            total=cpu_total,
            per_core=cpu_per_core,
            core_count=core_count,
            load_avg=load_avg
        )
        
        # 메모리 메트릭
        mem = psutil.virtual_memory()
        memory_snapshot = MemorySnapshot(
            total_gb=round(mem.total / (1024**3), 2),
            used_gb=round(mem.used / (1024**3), 2),
            free_gb=round(mem.free / (1024**3), 2),
            buffers_gb=round(mem.buffers / (1024**3), 2),
            cached_gb=round(mem.cached / (1024**3), 2),
            usage_pct=mem.percent
        )
        
        # 프로세스 메트릭 (상위 5개, CPU 기준)
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(ProcessSnapshot(
                    pid=proc.info['pid'],
                    name=proc.info['name'],
                    cpu_pct=proc.info['cpu_percent'] or 0.0,
                    mem_pct=proc.info['memory_percent'] or 0.0
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        processes.sort(key=lambda x: x.cpu_pct, reverse=True)
        # 상위 30개 프로세스 (프론트에서 정렬/필터링 가능하게)
        top_processes = processes[:30]
        
        # 타임스탐프
        timestamp = datetime.now(timezone.utc).isoformat()
        
        return MonitorMessage(
            type="monitor.snapshot",
            cpu=cpu_snapshot,
            memory=memory_snapshot,
            top_processes=top_processes,
            timestamp=timestamp
        )
    except Exception as e:
        logger.error(f"메트릭 수집 실패: {e}")
        # 기본값 반환
        return MonitorMessage(
            type="monitor.snapshot",
            cpu=CPUSnapshot(total=0, per_core=[], core_count=0, load_avg=[0, 0, 0]),
            memory=MemorySnapshot(
                total_gb=0, used_gb=0, free_gb=0,
                buffers_gb=0, cached_gb=0, usage_pct=0
            ),
            top_processes=[],
            timestamp=datetime.now(timezone.utc).isoformat()
        )

# ============================================================
# WebSocket 엔드포인트
# ============================================================

@router.websocket("/monitor")
async def websocket_monitor(websocket: WebSocket):
    """
    WebSocket 실시간 모니터링 엔드포인트

    사용 예:
    - ws://localhost:8000/ws/monitor?token=<JWT from /api/auth/login>

    업데이트 주기: 5초 (개발자 확인 용이)

    메시지 형식:
    {
        "type": "monitor.snapshot",
        "cpu": {...},
        "memory": {...},
        "top_processes": [...],
        "timestamp": "2026-04-07T12:00:00+00:00"
    }
    """
    # URL 쿼리 파라미터에서 토큰 추출
    try:
        query_string = websocket.scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string) if query_string else {}
        token = query_params.get("token", [None])[0]
        logger.info(f"🔍 WebSocket 연결 요청: token={token}, query_string={query_string}")
    except Exception as e:
        logger.error(f"❌ 쿼리 파라미터 파싱 실패: {e}")
        await websocket.close(code=4001, reason="Invalid query parameters")
        return
    
    # 토큰 검증 (JWT)
    if not verify_token(token):
        logger.warning(f"⚠️ WebSocket 인증 실패 (invalid/expired JWT): token_present={bool(token)}")
        await websocket.close(code=4001, reason="Unauthorized: Invalid or missing token")
        return
    
    await websocket.accept()
    logger.info(f"✅ WebSocket 연결 수립 (token={token})")
    
    try:
        while True:
            # 연결 상태 확인
            if websocket.client_state == WebSocketState.DISCONNECTED:
                logger.info(f"🔌 연결이 이미 종료됨 (token={token})")
                break
            
            # 5초 간격 메트릭 수집 및 브로드캐스트 (개발자 확인 용이)
            try:
                await asyncio.sleep(5)

                # 재차 연결 상태 확인
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    break

                metrics = await collect_metrics()
                await websocket.send_json(metrics.model_dump())
                logger.debug(f"📤 메트릭 브로드캐스트: {metrics.timestamp}")
                
            except RuntimeError as e:
                # RuntimeError: "Websocket is not connected" 또는 유사한 에러
                logger.info(f"🔌 WebSocket 연결 종료 감지: {e}")
                break
            except Exception as e:
                logger.error(f"메트릭 전송 실패: {type(e).__name__}: {e}")
                # 연결이 끊긴 경우라면 루프 탈출
                if "closed" in str(e).lower() or "disconnected" in str(e).lower():
                    break
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket 연결 종료 (token={token})")
    except asyncio.CancelledError:
        logger.info(f"🔌 WebSocket 태스크 취소됨 (token={token})")
    except Exception as e:
        logger.error(f"WebSocket 예외: {type(e).__name__}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass
