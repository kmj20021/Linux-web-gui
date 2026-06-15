# Linux Web GUI

라즈베리파이 / Linux 서버를 브라우저에서 실시간으로 모니터링하고 웹 터미널로 조작할 수 있는 풀스택 웹 관리 시스템입니다.

---

## 주요 기능

- **실시간 모니터링 대시보드** — WebSocket으로 5초마다 CPU(코어별)/메모리/프로세스 상위 30개를 스트리밍, Recharts 차트로 시각화
- **웹 터미널 (Docker 샌드박스)** — xterm.js + Docker PTY, 메모리 256MB·CPU 0.5코어·프로세스 100개 제한, OSC 7 cwd 추적
- **JWT 인증** — bcrypt 해시 저장, admin/viewer 역할 분리, WebSocket은 쿼리 파라미터 토큰 방식
- **모니터링 이력** — APScheduler 1분 주기 스냅샷 저장, 기간·인터벌별 집계 API 제공
- **네트워크 모니터링** — 인터페이스 목록, 순간 트래픽(KB/s), 패킷 통계, 연결 상태
- **HTTPS 배포** — Nginx 리버스 프록시, TLS 1.2/1.3, HSTS, Rate Limit(10r/s), Certbot 자동 갱신

---

## 기술 스택

| 계층 | 기술 |
|---|---|
| 프론트엔드 | React 18 + Vite, react-router-dom, recharts, @xterm/xterm |
| 백엔드 | FastAPI + Uvicorn (Python 3.11), SQLAlchemy async, aiosqlite, APScheduler, psutil, bcrypt, JWT |
| DB | SQLite (`linux_web_gui.db`) |
| 배포 | Docker Compose, Nginx 1.24 (리버스 프록시 + TLS), Certbot (Let's Encrypt 자동 갱신) |

---

## 시스템 아키텍처

```
브라우저 (React 18 + Vite)
        │  HTTPS 443
        ▼
  ┌─────────────┐
  │  Nginx 1.24 │  리버스 프록시, TLS 종료, 정적 파일 서빙
  └──────┬──────┘
         │ /api/*  → REST
         │ /ws/*   → WebSocket
         ▼
  ┌──────────────────┐
  │ FastAPI + Uvicorn │  Python 3.11, ASGI 비동기
  └────────┬─────────┘
           │
    ┌──────▼──────┐      ┌─────────────────────┐
    │  SQLite DB  │      │  Docker 컨테이너     │
    │ web_users   │      │  (webterm:latest)    │
    │ monitor_    │      │  Ubuntu 22.04        │
    │  snapshots  │      │  메모리/CPU 제한     │
    └─────────────┘      └─────────────────────┘
```

---

## 디렉토리 구조

```
Linux-web-gui/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routers/
│   │   ├── auth.py          # 로그인, 로그아웃, 회원가입, 내 정보
│   │   ├── websocket.py     # 실시간 모니터링 WebSocket
│   │   ├── shell.py         # 웹터미널 세션 관리
│   │   ├── cpu.py           # CPU 메트릭
│   │   ├── memory.py        # 메모리 메트릭
│   │   ├── disk.py          # 디스크 메트릭
│   │   ├── process.py       # 프로세스 목록 및 종료
│   │   ├── network.py       # 네트워크 인터페이스/트래픽
│   │   ├── history.py       # 모니터링 이력 조회
│   │   └── admin.py         # 사용자 관리 (admin 전용)
│   └── core/
│       ├── database.py      # DB 연결 및 세션
│       ├── models.py        # SQLAlchemy 모델
│       └── security.py      # JWT 발급 및 검증
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
├── data/
│   └── linux_web_gui.db     # SQLite 데이터베이스
├── nginx/
│   └── nginx.conf           # Nginx 리버스 프록시 설정
├── Dockerfile.webterm        # 웹터미널 샌드박스 이미지
├── docker-compose.yml
└── docs/
```

---

## 빠른 시작 (Quick Start)

### 사전 요구사항

- Docker 및 Docker Compose 설치
- (HTTPS 사용 시) 도메인 및 공인 IP

### 1. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
DATABASE_URL=sqlite+aiosqlite:////app/linux_web_gui.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
DOMAIN_NAME=your-domain.com
```

### 2. 웹터미널 이미지 빌드

웹터미널 기능을 사용하려면 샌드박스 이미지를 먼저 빌드합니다.

```bash
docker build -f Dockerfile.webterm -t webterm:latest .
```

### 3. 서비스 실행

```bash
docker-compose up -d
```

### 4. 접속

- HTTP: `http://localhost`
- HTTPS (도메인 설정 시): `https://your-domain.com`

### Docker 이미지 (Docker Hub)

| 서비스 | 이미지 |
|---|---|
| Frontend | `<your-dockerhub-username>/linux_gui_frontend:latest` |
| Backend | `<your-dockerhub-username>/linux_gui_backend:latest` |

---

## API 엔드포인트 요약

모든 REST API는 `/api` 프리픽스를 사용합니다. WebSocket은 `/ws` 경로를 사용합니다.

### 인증 (`/api/auth`)

| 메서드 | 경로 | 설명 | 인증 필요 |
|---|---|---|---|
| POST | `/api/auth/login` | 로그인 → access_token 발급 | X |
| POST | `/api/auth/logout` | 로그아웃 (클라이언트 토큰 삭제) | O |
| POST | `/api/auth/register` | 회원가입 (기본 role: viewer) | X |
| GET | `/api/auth/me` | 현재 사용자 정보 조회 | O |

### 모니터링 (`/api/monitor`)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/monitor/cpu` | CPU 메트릭 (코어별 사용률) |
| GET | `/api/monitor/memory` | 메모리 메트릭 |
| GET | `/api/monitor/disks` | 전체 디스크 목록 |
| GET | `/api/monitor/disk` | 단일 디스크 메트릭 |
| GET | `/api/monitor/processes` | 프로세스 목록 (상위 30개) |
| POST | `/api/monitor/processes/{pid}/kill` | 프로세스 종료 (admin 전용) |
| GET | `/api/monitor/history` | 모니터링 이력 (`?period=1hour&interval=5min`) |
| GET | `/api/monitor/raw-history` | 원시 스냅샷 조회 |
| GET | `/api/monitor/stats` | 통계 요약 |

### 네트워크 (`/api/network`)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/network/interfaces` | 네트워크 인터페이스 목록 |
| GET | `/api/network/traffic` | 순간 트래픽 (KB/s) |
| GET | `/api/network/packets` | 패킷 통계 |
| GET | `/api/network/connections` | 활성 연결 목록 |

### 웹터미널 (`/api/shell`)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/shell/fs` | 파일시스템 탐색 |
| GET | `/api/shell/sessions` | 활성 세션 목록 |
| DELETE | `/api/shell/reset` | 세션 초기화 |

### 관리자 (`/api/admin`, admin 역할 전용)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/admin/users` | 전체 사용자 목록 |
| POST | `/api/admin/users` | 사용자 생성 |
| PATCH | `/api/admin/users/{user_id}` | 사용자 정보 수정 |
| DELETE | `/api/admin/users/{user_id}` | 사용자 삭제 |
| GET | `/api/admin/audit` | 로그인 이력 조회 |

### WebSocket

| 경로 | 설명 |
|---|---|
| `wss://your-domain.com/ws/monitor?token=<JWT>` | 실시간 모니터링 스트림 (5초 주기) — 토큰이 URL에 포함되므로 서버 로그 접근 통제 필요 |

---

## 보안 고려사항

- **JWT** — `HS256` 알고리즘, 만료 시간 설정 (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- **비밀번호** — bcrypt 해시 저장, 평문 저장 없음
- **역할 분리** — `admin` / `viewer` 두 가지 역할, 민감 작업(프로세스 종료, 사용자 관리)은 admin 전용
- **WebSocket 인증** — 헤더 방식 불가로 인해 쿼리 파라미터 토큰 방식 사용 (`?token=<JWT>`)
- **Docker 샌드박스** — 웹터미널은 격리된 컨테이너에서 실행, 메모리 256MB·CPU 0.5코어·프로세스 100개 제한
- **Nginx** — Rate Limit 10r/s, TLS 1.2/1.3만 허용, HSTS 헤더 적용
- **호스트 접근 최소화** — 백엔드 컨테이너는 `/var/log` 읽기 전용 마운트, `privileged: false`
- **SECRET_KEY** — `.env`로 분리 관리, 절대 코드에 하드코딩하지 않음
