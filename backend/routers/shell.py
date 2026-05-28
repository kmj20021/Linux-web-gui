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
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from starlette.websockets import WebSocketState

from core.security import ALGORITHM, SECRET_KEY

logger = logging.getLogger(__name__)

WEBTERM_HOME = Path('/home/webterm')

ACTIVE_SESSIONS: Dict[str, 'DockerSession'] = {}
USER_LATEST_SESSION: Dict[str, str] = {}

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

    def start(self, cols: int = 80, rows: int = 24) -> int:
        self.home_dir.mkdir(parents=True, exist_ok=True)
        os.chown(self.home_dir, 1000, 1000)

        master_fd, slave_fd = os.openpty()
        self.master_fd = master_fd

        size = struct.pack('HHHH', rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, size)

        cmd = [
            'docker', 'run', '--rm', '-i', '--tty',
            '--name', self.container_name,
            '-v', f'{self.home_dir}:/home/user:rw',
            '-m', '256m',
            '--cpus', '0.5',
            '--pids-limit', '100',
            '--network', 'bridge',
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

    def cleanup(self) -> None:
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

        try:
            subprocess.run(
                ['docker', 'rm', '-f', self.container_name],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass


def _decode_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload if payload.get('sub') else None
    except JWTError:
        return None


def _create_session_id(username: str) -> str:
    return f"{username}-{int(time.time() * 1000)}"


def _extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    return parts[1] if len(parts) == 2 and parts[0].lower() == 'bearer' else None


@router.websocket('/ws/shell')
async def websocket_shell(websocket: WebSocket):
    # 토큰 추출 및 인증
    try:
        query_string = websocket.scope.get('query_string', b'').decode()
        params = parse_qs(query_string) if query_string else {}
        token = params.get('token', [None])[0]
    except Exception:
        await websocket.close(code=4001, reason='Invalid query')
        return

    payload = _decode_token(token)
    if payload is None:
        await websocket.close(code=4001, reason='Unauthorized')
        return

    # admin role 만 터미널 접근 허용
    if payload.get('role') != 'admin':
        await websocket.close(code=4003, reason='Admin privileges required')
        return

    username = payload['sub']
    session_id = _create_session_id(username)
    session = DockerSession(session_id=session_id, username=username)

    await websocket.accept()
    logger.info(f'shell ws: session opening (user={username}, sid={session_id})')

    # 초기 메타데이터 전송
    await websocket.send_json({
        'type': 'meta',
        'session_id': session_id,
        'cwd': session.cwd,
        'user': 'user',
    })

    try:
        master_fd = session.start(cols=80, rows=24)
    except Exception as e:
        logger.error(f'shell ws: container start failed: {e}')
        await websocket.send_json({
            'type': 'data',
            'data': f'\r\n\x1b[31mError: 터미널을 시작하지 못했습니다: {e}\x1b[0m\r\n',
        })
        await websocket.close(code=1011, reason='Container start failed')
        return

    ACTIVE_SESSIONS[session_id] = session
    USER_LATEST_SESSION[username] = session_id
    logger.info(f'shell ws: Docker container started (sid={session_id})')

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
            except Exception as e:
                logger.error(f'ws read error: {e}')
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
    except Exception as e:
        logger.error(f'shell ws: unexpected error: {e}')
    finally:
        session.cleanup()
        ACTIVE_SESSIONS.pop(session_id, None)
        if USER_LATEST_SESSION.get(username) == session_id:
            USER_LATEST_SESSION.pop(username, None)
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info(f'shell ws: session closed (sid={session_id})')


@router.get('/api/shell/fs')
async def get_shell_filesystem(
    session_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    token = _extract_token_from_header(authorization)
    payload = _decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or missing token',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    username = payload['sub']

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

    return {
        'session_id': sid,
        'web_username': username,
        'current_user': 'user',
        'cwd': session.cwd,
        'tree': _build_tree(home_dir, '/home/user'),
    }


def _build_tree(host_path: Path, container_path: str) -> dict:
    node = {
        'name': Path(container_path).name or 'home',
        'path': container_path,
        'type': 'directory' if host_path.is_dir() else 'file',
    }
    if host_path.is_dir():
        children = []
        try:
            for child in sorted(host_path.iterdir()):
                child_container = container_path.rstrip('/') + '/' + child.name
                children.append(_build_tree(child, child_container))
        except PermissionError:
            pass
        node['children'] = children
    return node


@router.get('/api/shell/sessions')
async def list_shell_sessions(authorization: Optional[str] = Header(None)):
    token = _extract_token_from_header(authorization)
    payload = _decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or missing token',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    username = payload['sub']
    sessions = [
        {'session_id': sid, 'cwd': s.cwd, 'user': 'user'}
        for sid, s in ACTIVE_SESSIONS.items()
        if s.username == username
    ]
    return {'sessions': sessions, 'count': len(sessions)}


@router.delete('/api/shell/reset')
async def reset_shell_home(authorization: Optional[str] = Header(None)):
    token = _extract_token_from_header(authorization)
    payload = _decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or missing token',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    username = payload['sub']

    # 활성 세션이 있으면 정리 후 진행
    sids_to_remove = [
        sid for sid, s in ACTIVE_SESSIONS.items() if s.username == username
    ]
    for sid in sids_to_remove:
        session = ACTIVE_SESSIONS.get(sid)
        if session is not None:
            try:
                session.cleanup()
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
