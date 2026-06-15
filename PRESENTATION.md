# Linux Web GUI — 핵심 기능 구현 설명

---

## 목차

1. [시스템 전체 구조](#1-시스템-전체-구조)
2. [실시간 모니터링 대시보드](#2-실시간-모니터링-대시보드)
3. [웹 터미널 (Docker 샌드박스)](#3-웹-터미널-docker-샌드박스)
4. [JWT 인증 시스템](#4-jwt-인증-시스템)
5. [모니터링 이력 저장 및 조회](#5-모니터링-이력-저장-및-조회)
6. [네트워크 모니터링](#6-네트워크-모니터링)
7. [배포 아키텍처 (Docker + Nginx + HTTPS)](#7-배포-아키텍처-docker--nginx--https)

---

## 1. 시스템 전체 구조

```
브라우저 (React 18 + Vite)
        │  HTTPS 443
        ▼
  ┌─────────────┐
  │  Nginx 1.24 │  ← 리버스 프록시, TLS 종료, 정적 파일 서빙
  └──────┬──────┘
         │ /api/*  →  REST
         │ /ws/*   →  WebSocket
         ▼
  ┌─────────────────┐
  │ FastAPI + Uvicorn│  ← Python 3.11, ASGI 비동기 서버
  │                 │
  │  routers/       │
  │  ├ auth         │  JWT 로그인/회원가입
  │  ├ websocket    │  실시간 CPU·메모리 스트리밍
  │  ├ shell        │  Docker PTY 터미널
  │  ├ cpu          │  CPU 사용률 조회
  │  ├ memory       │  메모리 사용량 조회
  │  ├ process      │  프로세스 목록 조회
  │  ├ disk         │  디스크 사용 현황 조회
  │  ├ network      │  네트워크 인터페이스·트래픽
  │  └ history      │  모니터링 이력 집계
  └────────┬────────┘
           │
    ┌──────▼──────┐      ┌─────────────────────┐
    │  SQLite DB  │      │  Docker 컨테이너     │
    │             │      │  (webterm:latest)    │
    │ web_users   │      │  Ubuntu 22.04        │
    │ monitor_    │      │  메모리 256MB 제한   │
    │  snapshots  │      │  CPU 0.5코어 제한    │
    └─────────────┘      └─────────────────────┘
```

---

## 2. 실시간 모니터링 대시보드

### 핵심 목표
브라우저에서 서버의 CPU·메모리·프로세스 상태를 **실시간**으로 확인한다.

### 구현 흐름

```
[백엔드]                                [프론트엔드]
wsocket.py                              Dashboard.jsx

WebSocket 연결 수립 (JWT 검증)
        │
   5초 루프 시작
        │
   psutil 호출
   ├ cpu_percent(percpu=True)    →  코어별 CPU 사용률
   ├ virtual_memory()            →  메모리 used/free/cached
   └ process_iter()              →  상위 30개 프로세스 (CPU 기준 정렬)
        │
   JSON 직렬화 후 send_json()
                                         receive → Recharts 차트 갱신
                                         WebSocketStatus 컴포넌트로
                                         연결 상태 표시
```

### 핵심 코드 — 메트릭 수집 (`backend/routers/websocket.py`)

```python
# 상위 30개 프로세스 수집 후 CPU 내림차순 정렬
processes = []
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
    try:
        processes.append(ProcessSnapshot(...))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass  # 수집 도중 종료된 프로세스 무시

processes.sort(key=lambda x: x.cpu_pct, reverse=True)
top_processes = processes[:30]
```

### WebSocket 인증 처리

HTTP와 달리 WebSocket은 Authorization 헤더를 사용할 수 없다.  
→ 연결 URL의 쿼리 파라미터로 JWT를 전달하는 방식으로 해결했다.

```
ws://server/ws/monitor?token=<JWT>
```

```python
# 쿼리 파라미터에서 토큰 파싱
query_string = websocket.scope.get("query_string", b"").decode()
query_params = parse_qs(query_string)
token = query_params.get("token", [None])[0]

if not verify_token(token):
    await websocket.close(code=4001, reason="Unauthorized")
    return
```

### 메시지 구조

```json
{
  "type": "monitor.snapshot",
  "cpu": {
    "total": 23.4,
    "per_core": [18.0, 29.1, 22.3, 24.2],
    "core_count": 4,
    "load_avg": [0.52, 0.48, 0.41]
  },
  "memory": {
    "total_gb": 8.0,
    "used_gb": 3.2,
    "free_gb": 1.1,
    "buffers_gb": 0.3,
    "cached_gb": 3.4,
    "usage_pct": 40.0
  },
  "top_processes": [
    {"pid": 1234, "name": "python3", "cpu_pct": 12.3, "mem_pct": 1.8}
  ],
  "timestamp": "2026-05-12T10:00:00+00:00"
}
```

---

## 3. 웹 터미널 (Docker 샌드박스)

### 핵심 목표
사용자가 브라우저에서 실제 Linux 명령어를 입력하고, 서버 환경을 오염시키지 않으면서 결과를 확인할 수 있게 한다.

### 구현 흐름

```
브라우저 xterm.js
      │ WebSocket (/ws/shell?token=JWT)
      ▼
  shell.py (DockerSession)
      │
      ├─ os.openpty()          ← PTY 마스터/슬레이브 fd 생성
      │
      ├─ subprocess.Popen([
      │     'docker', 'run',
      │     '--rm', '-i', '--tty',
      │     '-m', '256m',        ← 메모리 제한
      │     '--cpus', '0.5',     ← CPU 제한
      │     '--pids-limit', '100', ← 프로세스 수 제한
      │     '-v', '{홈}:/home/user:rw',
      │     'webterm:latest', '/bin/bash'
      │  ], stdin=slave_fd, stdout=slave_fd)
      │
      ├─ loop.add_reader(master_fd, on_pty_readable)  ← 비동기 출력 읽기
      │
      └─ 두 비동기 태스크 동시 실행:
            read_pty()  ← PTY → WebSocket 출력 전달
            read_ws()   ← WebSocket 입력 → PTY 전달
```

### 왜 Docker 샌드박스인가?

| 방식 | 문제점 |
|------|--------|
| 서버에서 직접 bash 실행 | 사용자가 서버 파일 삭제·수정 가능, 보안 위험 |
| VM | 부팅 시간 길고 자원 소비 큼 |
| **Docker 컨테이너** | 격리된 환경, 빠른 시작, 자원 제한 가능 ✅ |

### 터미널 리사이즈 처리

브라우저 창 크기가 바뀔 때 PTY 크기를 동기화한다.

```python
def resize(self, cols: int, rows: int) -> None:
    size = struct.pack('HHHH', rows, cols, 0, 0)
    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
```

프론트엔드는 `{"type": "resize", "cols": 120, "rows": 40}` 메시지를 전송한다.

### 현재 디렉토리 추적 (OSC 7)

`cd` 명령 후 xterm.js 파일 탐색기가 현재 경로를 알아야 한다.  
bash의 `PROMPT_COMMAND`에 OSC 7 이스케이프 시퀀스를 삽입하여 cwd를 전달한다.

```bash
# 컨테이너 .bashrc에 자동 삽입
PROMPT_COMMAND='printf "\033]7;%s\007" "$PWD"'
```

```python
# 백엔드에서 OSC 7 파싱 → cwd 추출 → 프론트엔드로 meta 메시지 전송
def process_output(self, raw: bytes) -> tuple[str, Optional[str]]:
    # '\x1b]7;/home/user/mydir\x07' 패턴 파싱
    ...
    if self._osc_buf.startswith('7;'):
        new_cwd = self._osc_buf[2:]
```

### 샌드박스 이미지 구성 (`Dockerfile.webterm`)

```dockerfile
FROM ubuntu:22.04
# bash, curl, vim, python3, git, ping, htop 등 학습 도구 포함
# 비root 사용자(uid=1000)로 실행 → 컨테이너 내 root 권한 없음
RUN useradd -u 1000 -g user -m -s /bin/bash user
USER user
```

---

## 4. JWT 인증 시스템

### 핵심 목표
stateless 토큰 방식으로 사용자 인증을 처리하고, 비밀번호는 복호화 불가능한 형태로 저장한다.

### 인증 흐름

```
[로그인]
POST /api/auth/login
  { username, password }
        │
  DB에서 username 조회
        │
  bcrypt.verify(입력 pw, 저장된 해시)
        │ 일치
  JWT 생성 { sub: username, role: viewer/admin, exp: 만료시각 }
        │
  { access_token, expires_in: 86400 }
        ▼
  브라우저 localStorage에 저장
        │
  이후 모든 요청: Authorization: Bearer <token>
        │
  get_current_user() 의존성 → 토큰 검증 → DB에서 사용자 조회
```

### 비밀번호 보안

평문 비밀번호는 서버에 저장되지 않는다. bcrypt 해시만 저장된다.

```python
# 저장: 평문 → bcrypt 해시 (salt 자동 포함)
hashed = pwd_context.hash("user_password")

# 검증: 평문과 해시 비교 (복호화 없이 검증)
is_valid = pwd_context.verify("user_password", hashed)
```

### 회원가입 유효성 검사 (Pydantic v2)

```python
class RegisterRequest(BaseModel):
    username: str  # 3~20자, 영문/숫자/언더스코어만
    password: str  # 8자 이상
    password_confirm: str

    @field_validator("username")
    def _validate_username(cls, v):
        if not re.match(r"^[A-Za-z0-9_]{3,20}$", v):
            raise ValueError("...")
        return v

    @model_validator(mode="after")
    def _validate_password_match(self):
        if self.password != self.password_confirm:
            raise ValueError("비밀번호가 일치하지 않습니다")
        return self
```

### 사용자 역할 구조

| role | 설명 |
|------|------|
| `admin` | 서버 시작 시 자동 생성되는 기본 계정 |
| `viewer` | 회원가입으로 생성되는 일반 계정 |

> 회원가입 API는 항상 `role="viewer"`로 고정하여, 외부에서 admin 계정을 생성할 수 없다.

---

## 5. 모니터링 이력 저장 및 조회

### 핵심 목표
실시간 데이터는 새로고침하면 사라진다. 과거 1시간~24시간의 CPU·메모리 추이를 조회할 수 있어야 한다.

### 구현 흐름

```
[저장 — APScheduler]
앱 시작 시 스케줄러 등록
        │
   1분마다 save_monitor_snapshot() 호출
        │
   psutil로 현재 메트릭 수집
        │
   MonitorSnapshot 레코드 생성 후 SQLite에 INSERT
        │
   coalesce=True → 지연 실행이 중첩돼도 1회만 실행

[조회 — history router]
GET /api/monitor/history?period=1hour&interval=5min
        │
   period → 조회 시작 시각 계산 (now - 1hour)
        │
   SQLAlchemy: recorded_at >= start_time 조건으로 SELECT
        │
   interval 단위로 CPU/메모리 평균·최소·최대 집계
        │
   HistoryResponse 반환 → 프론트엔드 차트 렌더링
```

### DB 스키마 (`monitor_snapshots` 테이블)

```
id            INTEGER  PK
cpu_total     FLOAT    전체 CPU 사용률
cpu_per_core  JSON     [18.0, 29.1, 22.3, 24.2]
core_count    INTEGER
load_avg      JSON     [load_1m, load_5m, load_15m]
mem_total_gb  FLOAT
mem_used_gb   FLOAT
mem_free_gb   FLOAT
mem_buffers_gb FLOAT
mem_cached_gb  FLOAT
mem_usage_pct  FLOAT
top_processes  JSON    상위 5개 프로세스
recorded_at   DATETIME INDEX (조회 성능 최적화)
```

### SQLite를 선택한 이유

- 별도 DB 서버 없이 단일 파일(`linux_web_gui.db`)로 운영 가능
- Docker 볼륨 마운트(`./data/linux_web_gui.db`)로 컨테이너 재시작 후에도 데이터 유지
- SQLAlchemy async + aiosqlite로 비동기 처리

---

## 6. 네트워크 모니터링

### 제공 API

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/network/interfaces` | 인터페이스 목록 (IP, MAC, MTU, 상태) |
| `GET /api/network/traffic` | 인터페이스별 송수신 속도 (KB/s) |
| `GET /api/network/packets` | 패킷 수, 오류, 드롭 통계 |

### 트래픽 속도 계산

psutil의 `net_io_counters()`는 **누적 바이트 수**만 반환한다.  
순간 속도(KB/s)를 구하려면 이전 호출값과 경과 시간을 비교해야 한다.

```python
_traffic_cache: Dict[str, Dict] = {}  # 인터페이스별 직전 측정값 캐시

# 이번 호출
prev = _traffic_cache.get(iface_name)
elapsed = now - prev["timestamp"]

sent_diff = c.bytes_sent - prev["bytes_sent"]
bytes_sent_rate = round((sent_diff / elapsed) / 1024.0, 2)  # KB/s

# 캐시 갱신
_traffic_cache[iface_name] = {"bytes_sent": c.bytes_sent, "timestamp": now}
```

카운터 리셋(리부팅 등으로 음수가 되는 경우) 시 0으로 처리해 오류를 방지한다.

---

## 7. 배포 아키텍처 (Docker + Nginx + HTTPS)

### 컨테이너 구성

```yaml
# docker-compose.yml
services:
  frontend:   # Nginx 1.24 + React 빌드 파일 (포트 80, 443)
  backend:    # FastAPI + Uvicorn (포트 8000, 내부만 노출)
  certbot:    # Let's Encrypt 인증서 12시간마다 자동 갱신
```

### Nginx 요청 흐름

```
클라이언트
    │ HTTP :80
    ▼
Nginx → 301 redirect → HTTPS :443
    │
    ├── location /        → /usr/share/nginx/html (React SPA)
    │                        try_files $uri /index.html
    │
    ├── location /api/    → proxy_pass backend:8000
    │                        Rate limit: 10r/s, burst 20
    │
    └── location /ws/     → proxy_pass backend:8000
                             Upgrade: websocket
                             proxy_read_timeout: 86400s
```

### 보안 설정

| 항목 | 설정값 |
|------|--------|
| TLS 버전 | TLS 1.2 / 1.3만 허용 |
| HSTS | max-age=31536000; includeSubDomains |
| X-Frame-Options | DENY |
| X-Content-Type-Options | nosniff |
| Rate Limiting | IP당 10req/s, burst 20 |
| 파일 업로드 | 최대 20MB |

### 멀티 스테이지 빌드

빌드 도구(Node.js)와 서빙 이미지(Nginx)를 분리해 최종 이미지 크기를 최소화했다.

```dockerfile
# Stage 1: React 빌드
FROM node:20-alpine as builder
RUN npm run build

# Stage 2: Nginx 서빙 (빌드 결과물만 복사)
FROM nginx:1.24-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

### 백엔드 Docker 소켓 마운트

웹 터미널 기능에서 사용자 요청마다 Docker 컨테이너를 생성해야 한다.  
백엔드 컨테이너에 호스트의 Docker 소켓을 마운트하여 컨테이너 안에서 컨테이너를 실행(DooD 방식)한다.

```yaml
backend:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # Docker CLI 사용 가능
    - /home/webterm:/home/webterm                # 사용자 홈 디렉토리 공유
```

---

## 핵심 기술 선택 요약

| 문제 | 선택한 해결책 | 이유 |
|------|-------------|------|
| 실시간 데이터 전달 | WebSocket | REST 폴링보다 낮은 지연, 서버 Push 가능 |
| 터미널 격리 | Docker 컨테이너 | 서버 환경 보호, 자원 제한 가능 |
| 인증 | JWT (stateless) | 서버 세션 없이 확장 가능, WebSocket에도 적용 가능 |
| DB | SQLite | 단일 파일, 별도 서버 불필요, 학습 이력 저장에 충분한 용량 |
| 비동기 처리 | FastAPI + asyncio | 다수의 WebSocket 연결을 단일 스레드로 처리 |
| SSL 인증서 | Let's Encrypt + Certbot | 무료, 자동 갱신 (12시간 주기) |
