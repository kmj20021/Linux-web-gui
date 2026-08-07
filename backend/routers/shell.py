"""
Docker PTY Shell Router

Endpoints:
- WebSocket /ws/shell        - Docker 컨테이너 PTY 브릿지
- GET /api/shell/fs          - 사용자 홈 디렉토리 파일 트리
- GET /api/shell/sessions    - 활성 세션 목록 (디버그용)
"""
from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import shutil
import struct
import subprocess
import termios
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from core.database import AsyncSessionLocal
from core.models import WebUser
from core.security import consume_ws_ticket, get_current_user
from services.file_tree import FileTreeError, build_lazy_tree
from sqlalchemy import select

logger = logging.getLogger(__name__)

WEBTERM_HOME = Path('/home/webterm')

ACTIVE_SESSIONS: Dict[str, 'DockerSession'] = {}
USER_LATEST_SESSION: Dict[str, str] = {}
MAX_SHELL_SESSIONS_PER_USER = 1
MAX_SHELL_SESSIONS_GLOBAL = 5
START_EARLY_EXIT_CHECKS = 4
START_EARLY_EXIT_INTERVAL_SECONDS = 0.05

router = APIRouter(tags=["Shell"])


class DockerSession:
    def __init__(self, session_id: str, username: str):
        self.session_id = session_id
        self.username = username
        self.master_fd: Optional[int] = None
        self.proc: Optional[subprocess.Popen] = None
        self.cwd = '/home/user'
        self.container_name = f'webterm-{session_id}'
        self.home_dir = WEBTERM_HOME / username
        # OSC 7 파싱 상태
        self._in_osc = False
        self._osc_buf = ''
        self._cleaned = False
        # PERF-02: cleanup 을 executor 스레드로 offload 하므로 단 한 번만
        # 실행되도록 check-and-set 을 스레드 안전하게 보호한다.
        self._cleanup_lock = threading.Lock()

    def _remove_named_orphan(self) -> None:
        """Remove only this session's deterministic container name."""
        subprocess.run(
            ['docker', 'rm', '-f', self.container_name],
            capture_output=True,
            timeout=5,
            check=False,
        )

    def start(self, cols: int = 80, rows: int = 24) -> int:
        self.home_dir.mkdir(parents=True, exist_ok=True)
        os.chown(self.home_dir, 1000, 1000)

        master_fd, slave_fd = os.openpty()
        self.master_fd = master_fd

        size = struct.pack('HHHH', rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, size)

        # A previous daemon restart may leave this deterministic name behind.
        self._remove_named_orphan()

        cmd = [
            'docker', 'run', '--rm', '-i', '--tty',
            '--name', self.container_name,
            '-v', f'{self.home_dir}:/home/user:rw',
            '-m', '256m',
            '--cpus', '0.5',
            '--pids-limit', '100',
            '--network', 'none',
            '--read-only',
            '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges',
            '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m',
            '--tmpfs', '/run:rw,noexec,nosuid,size=16m',
            '--user', '1000:1000',
            '-e', 'HOME=/home/user',
            '-e', 'USER=user',
            '-e', r'PS1=\u@\h:\w\$ ',
            '-e', r'PROMPT_COMMAND=printf "\033]7;%s\007" "$PWD"',
            '-w', '/home/user',
            'webterm:latest',
            '/bin/bash', '--login',
        ]

        self.proc = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)

        for _ in range(START_EARLY_EXIT_CHECKS):
            if self.proc.poll() is not None:
                self.cleanup()
                raise RuntimeError('webterm container exited during startup')
            time.sleep(START_EARLY_EXIT_INTERVAL_SECONDS)
        return master_fd

    def resize(self, cols: int, rows: int) -> None:
        if self.master_fd is not None:
            try:
                size = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
            except Exception:
                pass

    def process_output(self, raw: bytes) -> tuple[str, Optional[str]]:
        """PTY 출력에서 OSC 7 시퀀스를 파싱해 cwd를 추출하고 나머지 텍스트를 반환."""
        text = raw.decode('utf-8', errors='replace')
        result: list[str] = []
        new_cwd: Optional[str] = None
        i = 0
        while i < len(text):
            ch = text[i]
            if self._in_osc:
                if ch == '\x07':  # BEL: OSC 종료
                    if self._osc_buf.startswith('7;'):
                        new_cwd = self._osc_buf[2:]
                    self._osc_buf = ''
                    self._in_osc = False
                elif ch == '\x1b' and i + 1 < len(text) and text[i + 1] == '\\':
                    if self._osc_buf.startswith('7;'):
                        new_cwd = self._osc_buf[2:]
                    self._osc_buf = ''
                    self._in_osc = False
                    i += 1
                else:
                    self._osc_buf += ch
            elif ch == '\x1b' and i + 1 < len(text) and text[i + 1] == ']':
                self._in_osc = True
                self._osc_buf = ''
                i += 1
            else:
                result.append(ch)
            i += 1
        return ''.join(result), new_cwd

    async def start_async(self, cols: int = 80, rows: int = 24) -> int:
        """PERF-02: 블로킹 컨테이너 시작(docker rm/run·sleep)을 executor로 옮긴다."""
        return await asyncio.to_thread(self.start, cols, rows)

    async def cleanup_async(self) -> None:
        """PERF-02: 블로킹 정리(proc wait·docker rm)를 executor로 옮긴다.

        정리는 멱등하며(``_cleaned`` 가드) 실행은 정확히 한 번만 일어난다.
        """
        await asyncio.to_thread(self.cleanup)

    def cleanup(self) -> None:
        # check-and-set 을 스레드 안전하게: 두 스레드가 동시에 진입해도 본문은
        # 한 번만 실행된다.
        with self._cleanup_lock:
            if self._cleaned:
                return
            self._cleaned = True

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

        if self.proc is not None:
            if self.proc.poll() is None:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=2)
            self.proc = None

        try:
            self._remove_named_orphan()
        except Exception:
            pass


def _session_capacity_error(username: str) -> Optional[str]:
    if sum(session.username == username for session in ACTIVE_SESSIONS.values()) >= MAX_SHELL_SESSIONS_PER_USER:
        return 'Shell session limit reached for this user'
    if len(ACTIVE_SESSIONS) >= MAX_SHELL_SESSIONS_GLOBAL:
        return 'Shell service is at capacity'
    return None


def _create_session_id(username: str) -> str:
    return f"{username}-{int(time.time() * 1000)}"


@router.websocket('/ws/shell')
async def websocket_shell(websocket: WebSocket):
    try:
        query = websocket.scope.get('query_string', b'').decode('ascii')
    except UnicodeDecodeError:
        await websocket.close(code=4001, reason='Unauthorized')
        return
    query_keys = {part.split('=', 1)[0] for part in query.split('&') if part}
    if {'token', 'ticket'} & query_keys:
        await websocket.close(code=4001, reason='Unauthorized')
        return

    await websocket.accept()
    try:
        authentication = await asyncio.wait_for(websocket.receive_json(), timeout=5)
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError, TypeError):
        await websocket.close(code=4001, reason='Unauthorized')
        return
    if not isinstance(authentication, dict) or authentication.get('type') != 'authenticate':
        await websocket.close(code=4001, reason='Unauthorized')
        return
    username = await consume_ws_ticket(authentication.get('ticket'), 'shell')
    if username is None:
        await websocket.close(code=4001, reason='Unauthorized')
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(WebUser).where(WebUser.username == username))
        user = result.scalar_one_or_none()
    # 셸은 admin 전용이 아니라 인증된 사용자(admin·viewer) 모두 허용한다
    # (OUT_OF_PLAN_CHANGE 2026-08-07). 비활성 사용자만 여기서 재확인해 거부한다.
    if user is None or not user.is_active:
        await websocket.close(code=4003, reason='Unauthorized')
        return

    session_id = _create_session_id(username)
    session = DockerSession(session_id=session_id, username=username)
    logger.info('shell_ws user=%s result=%s', username, 'opened')

    # 초기 메타데이터 전송
    await websocket.send_json({
        'type': 'meta',
        'session_id': session_id,
        'cwd': session.cwd,
        'user': 'user',
    })

    capacity_error = _session_capacity_error(username)
    if capacity_error is not None:
        logger.info('shell_ws user=%s result=%s', username, 'capacity_rejected')
        await websocket.send_json({'type': 'data', 'data': f'\r\n{capacity_error}.\r\n'})
        await websocket.close(code=1013, reason='Shell capacity reached')
        return

    try:
        master_fd = await session.start_async(80, 24)
    except Exception:
        logger.error('shell_ws user=%s result=%s', username, 'container_start_failed')
        await session.cleanup_async()
        await websocket.send_json({
            'type': 'data',
            'data': '\r\n\x1b[31mError: terminal could not be started.\x1b[0m\r\n',
        })
        await websocket.close(code=1011, reason='Container start failed')
        return

    ACTIVE_SESSIONS[session_id] = session
    USER_LATEST_SESSION[username] = session_id
    logger.info('shell_ws user=%s result=%s', username, 'started')

    loop = asyncio.get_event_loop()
    read_queue: asyncio.Queue = asyncio.Queue()

    def on_pty_readable():
        try:
            data = os.read(master_fd, 4096)
            if data:
                read_queue.put_nowait(data)
            else:
                read_queue.put_nowait(None)
                loop.remove_reader(master_fd)
        except OSError:
            read_queue.put_nowait(None)
            loop.remove_reader(master_fd)

    loop.add_reader(master_fd, on_pty_readable)

    async def read_pty():
        try:
            while True:
                data = await read_queue.get()
                if data is None:
                    break
                text, new_cwd = session.process_output(data)
                if new_cwd is not None:
                    session.cwd = new_cwd
                    if websocket.client_state != WebSocketState.DISCONNECTED:
                        try:
                            await websocket.send_json({
                                'type': 'meta',
                                'session_id': session_id,
                                'cwd': new_cwd,
                                'user': 'user',
                            })
                        except Exception:
                            pass
                if text and websocket.client_state != WebSocketState.DISCONNECTED:
                    try:
                        await websocket.send_json({'type': 'data', 'data': text})
                    except Exception:
                        break
        finally:
            try:
                loop.remove_reader(master_fd)
            except Exception:
                pass

    async def read_ws():
        while True:
            try:
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    break
                msg = await websocket.receive_text()
                try:
                    d = json.loads(msg)
                    if isinstance(d, dict) and d.get('type') == 'resize':
                        session.resize(int(d.get('cols', 80)), int(d.get('rows', 24)))
                        continue
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass
                try:
                    os.write(master_fd, msg.encode('utf-8'))
                except OSError:
                    break
            except WebSocketDisconnect:
                break
            except Exception:
                logger.error('shell_ws user=%s result=%s', username, 'read_failed')
                break

    try:
        tasks = [
            asyncio.create_task(read_pty()),
            asyncio.create_task(read_ws()),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    except Exception:
        logger.error('shell_ws user=%s result=%s', username, 'unexpected_error')
    finally:
        # PERF-02: 취소·timeout 로 offload 정리가 중단돼도 cleanup 은 멱등하므로
        # 정확히 한 번만 실행된다. shield 로 정리 자체는 취소로부터 보호한다.
        try:
            await asyncio.shield(session.cleanup_async())
        except asyncio.CancelledError:
            session.cleanup()
        except Exception:
            session.cleanup()
        ACTIVE_SESSIONS.pop(session_id, None)
        if USER_LATEST_SESSION.get(username) == session_id:
            USER_LATEST_SESSION.pop(username, None)
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info('shell_ws user=%s result=%s', username, 'closed')


@router.get('/api/shell/fs')
async def get_shell_filesystem(
    session_id: Optional[str] = Query(None),
    path: str = Query('/home/user'),
    current_user: WebUser = Depends(get_current_user),
):
    username = current_user.username

    sid = session_id or USER_LATEST_SESSION.get(username)
    if not sid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='No active shell session')

    session = ACTIVE_SESSIONS.get(sid)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Session {sid!r} not found')
    if session.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Not your session')

    home_dir = WEBTERM_HOME / username
    home_dir.mkdir(parents=True, exist_ok=True)

    try:
        tree = build_lazy_tree(home_dir, path)
    except FileTreeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return {
        'session_id': sid,
        'web_username': username,
        'current_user': 'user',
        'cwd': session.cwd,
        'tree': tree,
    }


@router.get('/api/shell/sessions')
async def list_shell_sessions(
    current_user: WebUser = Depends(get_current_user),
):
    # 셸은 인증된 사용자(admin·viewer) 모두 허용한다. get_current_user 는
    # 서명만 보는 게 아니라 DB 에서 사용자 활성 상태를 재확인한다.
    username = current_user.username
    sessions = [
        {'session_id': sid, 'cwd': s.cwd, 'user': 'user'}
        for sid, s in ACTIVE_SESSIONS.items()
        if s.username == username
    ]
    return {'sessions': sessions, 'count': len(sessions)}


@router.delete('/api/shell/reset')
async def reset_shell_home(
    current_user: WebUser = Depends(get_current_user),
):
    # 홈 초기화는 파일을 지우는 동작이므로 비활성 사용자를 서버에서 막는다. 인증된
    # 사용자(admin·viewer)는 모두 허용하되 본인 홈 디렉터리만 건드릴 수 있다
    # (OUT_OF_PLAN_CHANGE 2026-08-07: 셸을 일반 사용자에게 개방).
    username = current_user.username

    # 활성 세션이 있으면 정리 후 진행
    sids_to_remove = [
        sid for sid, s in ACTIVE_SESSIONS.items() if s.username == username
    ]
    for sid in sids_to_remove:
        session = ACTIVE_SESSIONS.get(sid)
        if session is not None:
            try:
                # PERF-02: 블로킹 정리를 executor 로 옮겨 이벤트 루프를 막지 않는다.
                await asyncio.to_thread(session.cleanup)
            except Exception as e:
                logger.error(f'shell reset: cleanup failed (sid={sid}): {e}')
        ACTIVE_SESSIONS.pop(sid, None)
    if USER_LATEST_SESSION.get(username) in sids_to_remove or username in USER_LATEST_SESSION:
        USER_LATEST_SESSION.pop(username, None)

    home_dir = WEBTERM_HOME / username
    try:
        if home_dir.exists():
            shutil.rmtree(home_dir)
        home_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chown(home_dir, 1000, 1000)
        except PermissionError:
            pass
    except Exception as e:
        logger.error(f'shell reset failed (user={username}): {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to reset home directory: {e}',
        )

    logger.info(f'shell reset: home directory cleared (user={username})')
    return {'reset': True, 'username': username}
