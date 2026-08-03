"""
WebSocket 실시간 모니터링 엔드포인트
CPU·메모리·프로세스 1초 간격 브로드캐스트
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import psutil
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4

from schemas.websocket import (
    CPUSnapshot,
    MemorySnapshot,
    ProcessSnapshot,
    MonitorMessage,
)
from core.database import AsyncSessionLocal
from core.models import WebUser
from core.security import consume_ws_ticket
from services.metrics_collector import get_collector
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# ============================================================
# 인증 및 헬퍼 함수
# ============================================================

def _has_auth_query(websocket: WebSocket) -> bool:
    """Reject credentials in URLs before the WebSocket handshake."""
    try:
        query = websocket.scope.get("query_string", b"").decode("ascii")
    except UnicodeDecodeError:
        return True
    keys = {part.split("=", 1)[0] for part in query.split("&") if part}
    return bool({"token", "ticket"} & keys)


async def _authenticate_monitor_ticket(websocket: WebSocket) -> bool:
    try:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=5)
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError, TypeError):
        return False
    if not isinstance(message, dict) or message.get("type") != "authenticate":
        return False
    username = await consume_ws_ticket(message.get("ticket"), "monitor")
    if username is None:
        return False
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(WebUser).where(WebUser.username == username))
        user = result.scalar_one_or_none()
    return user is not None and user.is_active

async def collect_metrics() -> MonitorMessage:
    """현재 시스템 메트릭을 수집한다.

    블로킹 psutil 호출(`cpu_percent(interval=...)` 등)은 이벤트 루프를 막지
    않도록 executor 스레드에서 실행한다(PERF-01).
    """
    return await asyncio.to_thread(_collect_metrics_blocking)


def _collect_metrics_blocking() -> MonitorMessage:
    """
    현재 시스템 메트릭 수집 (블로킹)
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

    연결 후 5초 내에 single-use monitor ticket을 인증한다.

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
    request_id = uuid4().hex

    if _has_auth_query(websocket):
        logger.warning(
            "websocket request_id=%s result=%s",
            request_id,
            "authentication_failed",
        )
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    if not await _authenticate_monitor_ticket(websocket):
        logger.warning(
            "websocket request_id=%s result=%s",
            request_id,
            "authentication_failed",
        )
        await websocket.close(code=4001, reason="Unauthorized")
        return

    logger.info(
        "websocket request_id=%s result=%s",
        request_id,
        "accepted",
    )

    # 단일 백그라운드 수집기의 최신 snapshot을 공유받는다(PERF-01).
    # 연결마다 수집하지 않으므로 연결 수가 늘어도 수집 횟수는 증가하지 않는다.
    collector = get_collector()

    try:
        while True:
            # 연결 상태 확인
            if websocket.client_state == WebSocketState.DISCONNECTED:
                logger.info(
                    "websocket request_id=%s result=%s",
                    request_id,
                    "disconnected",
                )
                break

            # 다음 수집 주기(기본 5초)까지 대기했다가 공유 snapshot을 브로드캐스트한다.
            try:
                metrics = await collector.wait_for_update()

                # 재차 연결 상태 확인
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    logger.info(
                        "websocket request_id=%s result=%s",
                        request_id,
                        "disconnected",
                    )
                    break

                await websocket.send_json(metrics.model_dump())
                logger.debug(
                    "websocket request_id=%s result=%s",
                    request_id,
                    "metrics_sent",
                )

            except RuntimeError:
                # RuntimeError: "Websocket is not connected" 또는 유사한 에러
                logger.info(
                    "websocket request_id=%s result=%s",
                    request_id,
                    "send_failed",
                )
                break
            except Exception:
                logger.error(
                    "websocket request_id=%s result=%s",
                    request_id,
                    "send_failed",
                )
                # 연결이 끊긴 경우라면 루프 탈출
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    break

    except WebSocketDisconnect:
        logger.info(
            "websocket request_id=%s result=%s",
            request_id,
            "disconnected",
        )
    except asyncio.CancelledError:
        logger.info(
            "websocket request_id=%s result=%s",
            request_id,
            "cancelled",
        )
    except Exception:
        logger.error(
            "websocket request_id=%s result=%s",
            request_id,
            "internal_error",
        )
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass
