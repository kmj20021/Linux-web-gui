# Linux Web GUI

Linux 서버를 브라우저에서 실시간 모니터링하고, 격리된 Docker 샌드박스 웹 터미널로
조작할 수 있는 학습용 풀스택 웹 관리 시스템입니다.

> **문서 상태**: 이 README는 현재 구현을 기준으로 합니다.
> 운영·로컬 개발 실행 절차는 `docs/operations.md`에 있습니다.

---

## 주요 기능

- **실시간 모니터링 대시보드** — 단일 백그라운드 수집기가 **5초마다** 스냅샷 1개를
  만들고 모든 WebSocket 연결이 이를 공유(fan-out)합니다. 연결이 늘어도 수집 횟수는
  늘지 않습니다.
- **웹 터미널 (Docker 샌드박스)** — xterm.js + Docker PTY. 네트워크 차단, 읽기 전용
  루트, 모든 capability 제거 등 최소 권한으로 실행됩니다.
- **JWT 인증 + 일회성 WebSocket ticket** — REST는 `Authorization: Bearer`, WebSocket은
  60초 이하 **일회용 ticket을 첫 메시지로** 전달합니다. 토큰·ticket은 URL과 로그에
  남지 않습니다.
- **모니터링 이력** — 스케줄러가 스냅샷을 저장하고 기간·인터벌별 집계를 제공합니다.
  원본 스냅샷은 **7일 후 자동 삭제**됩니다.
- **네트워크 모니터링** — 인터페이스, 트래픽(KB/s), 패킷 통계, 연결 상태.
- **교육용 시뮬레이션 페이지** — 가상 파일시스템과 네트워크 진단 도구는 브라우저
  안에서만 동작하며 화면에 시뮬레이션임을 항상 표시합니다.
- **HTTPS 배포** — Nginx 리버스 프록시, TLS 1.2/1.3, HSTS, Certbot 자동 갱신.
  **운영 프로필은 인증서가 없으면 시작하지 않습니다.**

---

## 기술 스택

| 계층 | 기술 |
|---|---|
| 프론트엔드 | React 18 + Vite, react-router-dom, recharts, @xterm/xterm |
| 백엔드 | FastAPI + Uvicorn (Python 3.11), SQLAlchemy async, aiosqlite, Alembic, APScheduler, psutil, bcrypt, JWT |
| DB | SQLite — 스키마는 **Alembic 마이그레이션**으로 관리 |
| 테스트 | pytest (backend), Vitest + Testing Library + axe (frontend) |
| 배포 | Docker Compose, Nginx (리버스 프록시 + TLS), Certbot, docker-socket-proxy |

---

## 시스템 아키텍처

```
브라우저 (React 18 + Vite)
        │  HTTPS 443
        ▼
  ┌─────────────┐
  │    Nginx    │  리버스 프록시, TLS 종료, 정적 파일 서빙
  └──────┬──────┘
         │ /api/*  → REST
         │ /ws/*   → WebSocket
         ▼
  ┌───────────────────┐
  │ FastAPI + Uvicorn │  내부 expose 8000 (호스트에 공개하지 않음)
  └────────┬──────────┘
           │
    ┌──────▼──────┐   ┌──────────────────────┐   ┌─────────────────┐
    │  SQLite DB  │   │ docker-socket-proxy  │──▶│ 셸 컨테이너      │
    │ web_users   │   │ (제한된 Docker API)   │   │ network: none   │
    │ monitor_    │   └──────────────────────┘   │ read-only rootfs │
    │  snapshots  │                              │ cap-drop ALL     │
    └─────────────┘                              └─────────────────┘
```

백엔드는 호스트의 Docker 소켓에 **직접 접근하지 않습니다.** 최소 권한 프록시를
거칩니다.

---

## 디렉토리 구조

```
linux-web-gui/
├── backend/
│   ├── main.py                  # FastAPI 앱, 라우터 등록, 시작/종료 lifecycle
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── cli/
│   │   └── create_admin.py      # 최초 관리자 생성 (대화형 전용)
│   ├── core/
│   │   ├── database.py          # DB 연결·세션
│   │   ├── models.py            # SQLAlchemy 모델
│   │   ├── security.py          # JWT, ticket, 인증 의존성
│   │   └── db_migrations.py     # 시작 시 alembic upgrade head (fail-closed)
│   ├── migrations/              # Alembic 리비전
│   ├── routers/
│   │   ├── auth.py              # 로그인·로그아웃·회원가입·내 정보·ticket 발급
│   │   ├── admin.py             # 사용자·감사 로그 관리 (admin 전용)
│   │   ├── websocket.py         # /ws/monitor 실시간 스트림
│   │   ├── shell.py             # /ws/shell, 셸 세션·파일 탐색
│   │   ├── cpu.py memory.py disk.py process.py network.py history.py
│   ├── schemas/                 # Pydantic 응답 모델
│   ├── services/
│   │   ├── metrics_collector.py # 단일 수집기 + 공유 fan-out
│   │   ├── scheduler.py         # 스냅샷 저장, 보존 job
│   │   └── file_tree.py         # 경계 안전한 디렉터리 나열
│   ├── tests/                   # pytest (현재 자동 검사)
│   └── test/                    # 과거 수동 스크립트·보고서 (역사 기록)
├── frontend/
│   ├── vite.config.js  vitest.config.js  eslint.config.js
│   ├── nginx.conf  nginx-http.conf  start.sh
│   └── src/
│       ├── api/client.js        # 공통 REST 계층 (apiFetch, ApiError, 401 처리)
│       ├── components/  context/  hooks/  pages/  styles/
│       ├── features/            # 기능별 모듈
│       │   ├── filesystem/          # 교육용 가상 파일시스템
│       │   ├── network-diagnostics/ # 교육용 진단 시뮬레이터
│       │   └── users/               # 사용자 관리 API·UI
│       └── test/                # 공통 테스트 설정, 접근성 검사
├── scripts/
│   ├── gate.sh                  # 표준 검증 게이트 실행기
│   └── security_scan.py         # 소스 비밀·민감 로그 스캐너
├── docs/                        # 계획·계약·운영 문서
├── data/                        # 실행 DB (Git 미추적)
├── Dockerfile.webterm           # 웹터미널 샌드박스 이미지
├── docker-compose.yml           # 운영 프로필
└── docker-compose.dev.yml       # 개발 override (HTTP 허용)
```

---

## 빠른 시작

자세한 절차·문제 해결은 **`docs/operations.md`** 를 참고하세요. 아래는 요약입니다.

### 1. 환경변수

프로젝트 루트에 `.env`를 만듭니다. **모두 필수이며 값이 없으면 기동에 실패합니다.**

```env
SECRET_KEY=<openssl rand -hex 32 등으로 생성한 임의 값>
DATABASE_URL=sqlite+aiosqlite:////app/linux_web_gui.db
DOMAIN_NAME=your-domain.com
```

> 도메인이 없는 환경이면 `DOMAIN_NAME`에 **고정 공인 IP**를 넣고 개발 프로필로
> 실행합니다. IP에는 TLS 인증서를 발급받을 수 없으므로 운영 프로필은 실행되지
> 않습니다. 위험과 절차는 `docs/operations.md` §4.3을 보세요.

> `SECRET_KEY`에 `changeme`, `secret`, `placeholder` 같은 **알려진 placeholder를 넣으면
> 서버가 시작을 거부합니다.** 기본 관리자 계정도 자동 생성되지 않습니다.

### 2. 웹터미널 이미지 빌드

```bash
docker build -f Dockerfile.webterm -t webterm:latest .
```

### 3. 실행

```bash
# 도메인이 있는 경우 — 운영 (HTTPS, 인증서 필수)
docker compose up -d

# 도메인이 없거나 로컬 개발 — HTTP (개발 override)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

인증서 없이 운영 프로필을 띄우면 컨테이너가 **재시작 루프에 빠집니다**(의도된 동작).
`docker compose up -d`는 성공한 것처럼 보이므로 `docker compose ps`로 `Restarting`
여부를 확인하세요.

### 4. 최초 관리자 생성

기본 관리자 계정은 만들어지지 않습니다. 다음 명령으로 **직접** 만듭니다.

```bash
docker compose exec backend python -m cli.create_admin
```

사용자명과 비밀번호를 대화형으로 입력받습니다. 이력에 남지 않도록 **명령행 인자로
자격증명을 받지 않으며**, 비밀번호와 해시를 출력하지 않습니다.
(사용자명 3~20자 영숫자·밑줄, 비밀번호 8자 이상)

---

## API 엔드포인트와 권한 행렬

REST는 `/api`, WebSocket은 `/ws` 프리픽스를 씁니다. 권한은 **서버가 강제**하며 UI는
표시에만 사용합니다. 기준 계약은 `docs/contracts/security-contract.md`입니다.

- 인증 정보가 없거나 유효하지 않거나 **사용자가 비활성화된 경우 401**
- 인증됐지만 역할·소유권을 벗어나면 **403**
- 없는 리소스 **404**, 형식 오류 **422**

### 헬스 체크

| 메서드 | 경로 | 미인증 | 설명 |
|---|---|---|---|
| GET | `/api/health` | 허용 | 컨테이너 healthcheck 용. 인증 없이 접근 가능하며 시스템 정보를 담지 않는다 |

### 인증 (`/api/auth`)

| 메서드 | 경로 | 미인증 | viewer | admin |
|---|---|---|---|---|
| POST | `/api/auth/login` | 허용 | 허용 | 허용 |
| POST | `/api/auth/register` | 허용 | 허용 | 허용 |
| POST | `/api/auth/logout` | 401 | 허용 | 허용 |
| GET | `/api/auth/me` | 401 | 허용 | 허용 |
| POST | `/api/auth/ws-tickets/monitor` | 401 | 허용 | 허용 |
| POST | `/api/auth/ws-tickets/shell` | 401 | **403** | 허용 |

### 모니터링 (`/api/monitor`)

| 메서드 | 경로 | 미인증 | viewer | admin |
|---|---|---|---|---|
| GET | `/api/monitor/cpu` | 401 | 허용 | 허용 |
| GET | `/api/monitor/memory` | 401 | 허용 | 허용 |
| GET | `/api/monitor/disks` | 401 | 허용 | 허용 |
| GET | `/api/monitor/disk` | 401 | 허용 | 허용 |
| GET | `/api/monitor/processes` | 401 | 허용 | 허용 |
| GET | `/api/monitor/history` | 401 | 허용 | 허용 |
| GET | `/api/monitor/raw-history` | 401 | 허용 | 허용 |
| GET | `/api/monitor/stats` | 401 | 허용 | 허용 |
| POST | `/api/monitor/processes/{pid}/kill` | 401 | **403** | **조건부 허용** |

프로세스 종료는 admin이라도 **이 앱이 만든 교육용 `demo-*` 자식 프로세스**만 가능합니다.
allowlist 밖·비자식·보호 PID는 403, 없는 PID는 404입니다.

### 네트워크 (`/api/network`)

| 메서드 | 경로 | 미인증 | viewer | admin |
|---|---|---|---|---|
| GET | `/api/network/interfaces` | 401 | 허용 | 허용 |
| GET | `/api/network/traffic` | 401 | 허용 | 허용 |
| GET | `/api/network/packets` | 401 | 허용 | 허용 |
| GET | `/api/network/connections` | 401 | **403** | 허용 |

연결 목록은 원격 주소와 PID를 포함하므로 admin 전용입니다.

### 웹터미널 (`/api/shell`)

| 메서드 | 경로 | 미인증 | viewer | admin |
|---|---|---|---|---|
| GET | `/api/shell/fs` | 401 | **403** | **본인 세션만** |
| GET | `/api/shell/sessions` | 401 | **403** | **본인 세션만** |
| DELETE | `/api/shell/reset` | 401 | **403** | **본인 세션만** |

웹 터미널은 admin 전용입니다. 세 경로 모두 요청 시 DB에서 **사용자 활성 상태와 현재
역할을 다시 확인**하므로, 계정을 비활성화하거나 viewer로 강등하면 기존 토큰이
만료되기 전이라도 즉시 차단됩니다.

admin이라도 **다른 사용자의 셸 세션·파일 영역은 열람·초기화할 수 없습니다.**

### 관리자 (`/api/admin`)

| 메서드 | 경로 | 미인증 | viewer | admin |
|---|---|---|---|---|
| GET · POST | `/api/admin/users` | 401 | **403** | 허용 |
| PATCH · DELETE | `/api/admin/users/{user_id}` | 401 | **403** | 허용 |
| GET | `/api/admin/audit` | 401 | **403** | 허용 |

모든 admin은 `created_by`와 무관하게 동일한 범위를 가집니다(전역 관리자).
**마지막 활성 admin은 강등·비활성화·삭제할 수 없습니다.**

### 수집 실패 응답

CPU·메모리·디스크·네트워크 수집이 실패하면 0이나 빈 배열로 숨기지 않고 **503**을
반환합니다. 실제 0값과 실패를 구분할 수 있습니다.

```json
{ "detail": { "error": "collection_failed", "resource": "cpu" } }
```

---

## WebSocket 인증과 주기

| 경로 | 용도 | 권한 |
|---|---|---|
| `/ws/monitor` | 실시간 모니터링 스냅샷 (**5초 주기**) | 로그인 사용자 |
| `/ws/shell` | 웹 터미널 PTY | admin, 본인 세션만 |

**access token을 URL에 넣지 않습니다.** 흐름은 다음과 같습니다.

1. REST로 용도별 ticket을 발급받습니다.
   `POST /api/auth/ws-tickets/monitor` (또는 `/shell`) — `Authorization: Bearer` 필요.
   응답은 `Cache-Control: no-store`이며 `expires_in_seconds`는 **60 이하**입니다.
2. WebSocket에 연결한 뒤 **첫 메시지로만** ticket을 보냅니다.

   ```json
   { "type": "authenticate", "ticket": "<ticket>" }
   ```

3. 서버는 ticket을 원자적으로 **1회 소비**하고, DB에서 사용자 활성 상태와 **현재
   역할**을 다시 확인합니다. 인증 전에는 데이터·셸 입력을 처리하지 않습니다.

만료·재사용·용도 불일치(monitor ticket으로 shell 연결 등)·비활성 사용자는 모두
거부됩니다. ticket 원문은 URL·서버 로그·브라우저 콘솔 어디에도 남지 않습니다.

---

## 보안 경계

### 인증·비밀

- `SECRET_KEY` 미설정 또는 알려진 placeholder면 **서버가 시작하지 않습니다.**
- 기본 관리자(`admin/admin1234` 등) 자동 생성이 **없습니다.** CLI로만 만듭니다.
- 비밀번호는 bcrypt 해시로만 저장하며 평문·해시를 출력하지 않습니다.
- JWT·ticket·session ID는 로그, URL, 브라우저 콘솔, Nginx 접근 로그에 남기지 않습니다.
  `scripts/security_scan.py`가 소스에서 이를 검사합니다.

### 배포

- 백엔드는 호스트에 포트를 공개하지 않습니다(`expose`만 사용). 반드시 Nginx를 거칩니다.
- **운영 프로필은 TLS 인증서가 없으면 시작에 실패합니다.** HTTP fallback은 개발
  override(`APP_ENV=development`)에서만 허용됩니다.
- 필수 환경변수가 없으면 Compose 단계에서 실패합니다(fail-closed).
- **현재 배포 환경은 도메인 발급이 불가해 고정 IP + HTTP로 운영합니다.** 그 결과
  자격증명과 토큰이 평문으로 전송됩니다. 코드의 TLS 강제는 유지하되 이 환경에서는
  해당 경로를 쓰지 못하는 것이며, 완화책은 인바운드 소스 제한입니다.
  자세한 위험은 `docs/operations.md` §4.3과 §7을 보세요.

### 웹터미널 샌드박스

셸 컨테이너는 다음 제약으로 실행됩니다.

| 항목 | 값 |
|---|---|
| 네트워크 | `none` (외부 통신 불가) |
| 루트 파일시스템 | `--read-only` |
| capability | `--cap-drop ALL` |
| 권한 상승 | `--security-opt no-new-privileges` |
| 쓰기 가능 영역 | `/tmp` 64MB, `/run` 16MB tmpfs (`noexec,nosuid`) |
| 실행 사용자 | 비root (`1000:1000`) |
| 메모리 · CPU · PID | 256MB · 0.5코어 · 100개 |
| 동시 세션 | 사용자당 1개, 전체 5개 |

- 컨테이너에서 **Docker 소켓과 호스트 파일시스템에 접근할 수 없습니다.**
- 파일 탐색은 사용자 홈 밖으로 나갈 수 없습니다. 심볼릭 링크를 따라가지 않고
  (`lstat`), 깊이·항목 수·응답 크기·timeout 제한이 걸립니다.

---

## 개발 명령

### 검증 게이트 (권장)

모든 검사를 한 번에 실행합니다.

```bash
bash scripts/gate.sh          # 전체
bash scripts/gate.sh --fast   # npm ci·build 생략 (작업 중 확인용)
```

### 개별 명령

```bash
# 백엔드
python -m pytest backend/tests

# 프론트엔드
npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend test -- --run
npm --prefix frontend run build

# 배포 구성
docker compose config --quiet

# 소스 보안 스캔
python scripts/security_scan.py
```

프론트엔드 테스트에는 주요 페이지에 대한 **자동 접근성 검사(axe)** 와 키보드 조작
검증이 포함됩니다.

---

## 문제 해결

### OS별 `psutil` 차이

이 프로젝트는 Linux 배포를 전제로 하지만 개발은 Windows·macOS에서도 합니다.
`psutil`이 OS마다 다른 필드를 주는 곳이 있습니다.

| 항목 | Linux | Windows / macOS | 처리 |
|---|---|---|---|
| `virtual_memory().buffers` | 있음 | **없음** | `getattr(mem, "buffers", 0)`로 0 처리 |
| `virtual_memory().cached` | 있음 | **없음** | `getattr(mem, "cached", 0)`로 0 처리 |
| `getloadavg()` | 있음 | Windows는 모의값 | 값의 의미가 다름에 유의 |
| `net_connections()` | 전체 | 권한 부족 시 일부 누락 | 실패 시 503 반환 |

Windows에서 메모리 카드의 buffers·cached가 0으로 보이는 것은 **정상**입니다.

### 자주 겪는 문제

| 증상 | 원인과 조치 |
|---|---|
| 서버가 즉시 종료됨 | `SECRET_KEY` 미설정 또는 placeholder. 임의 값으로 교체하세요. |
| 운영 컨테이너가 시작하지 않음 | TLS 인증서가 없습니다. `docs/operations.md`의 인증서 발급 절차를 따르거나 개발 프로필로 실행하세요. `docker compose ps`에서 `Restarting`으로 보입니다. |
| 개발 프로필인데 브라우저가 HTTPS로 넘어감 | 운영 프로필로 먼저 접속했다면 브라우저가 `return 301`(영구 리디렉션)을 캐시한 것입니다. 컨테이너 문제가 아닙니다. 시크릿 창으로 확인하거나 해당 사이트의 캐시를 지우세요. `curl -sS -o /dev/null -w '%{http_code}\n' http://localhost/`가 200이면 서버는 정상입니다. |
| 로그인은 되는데 대시보드가 비어 있음 | WebSocket ticket 발급 실패. 브라우저 네트워크 탭에서 `/api/auth/ws-tickets/monitor` 응답을 확인하세요. |
| 터미널 안에서 `apt`·`ping`이 안 됨 | 의도된 동작입니다. 셸 컨테이너는 네트워크가 `none`입니다. |
| 터미널 세션 생성 실패 | 동시 세션 한도(사용자당 1, 전체 5)에 걸렸을 수 있습니다. |
| 메트릭이 503을 반환 | 수집 실패를 0으로 숨기지 않고 알리는 정상 동작입니다. 서버 로그의 `resource` 값을 확인하세요. |
| `docker compose config` 실패 | 필수 환경변수(`SECRET_KEY`·`DATABASE_URL`·`DOMAIN_NAME`) 누락입니다. |

---

## 문서

| 문서 | 내용 |
|---|---|
| `docs/operations.md` | 운영 배포·로컬 개발 실행 절차, 인증서, 백업 |
| `docs/contracts/security-contract.md` | 권한 행렬과 ticket 계약의 단일 기준 |
| `docs/db-operations.md` | DB 마이그레이션·백업·복구 절차 |
| `docs/tutorials/README.md` | 단계별 학습 과제 |
| `backend/test/*.md` | 과거 수동 테스트 보고서 (현재 결과 아님) |
