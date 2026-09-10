# INTERVIEW_PREP — linux-web-gui 면접 훈련 기록

> 매 세션 시작 시 이 파일을 먼저 읽는다. 세션 종료 시 진도표·약점·재질문 목록을 갱신한다.
> 훈련 규칙: `CLAUDE.md` (질문 우선, 추측 금지, 힌트는 요청 시에만)

- 시작일: 2026-09-06
- 최근 세션: 2026-09-09 (세션 2)

---

## 0. 프로젝트 사실 요약 (조사로 확인된 것만)

| 항목 | 확인 내용 |
|---|---|
| 진입점 | `backend/main.py` — FastAPI 앱 생성, 라우터 등록, `@app.on_event("startup"/"shutdown")` |
| 실행 | `uvicorn main:app --host 0.0.0.0 --port 8000` (컨테이너는 `expose: 8000`, 호스트 미공개) |
| 라우터 | `auth, admin, cpu, memory, process, disk, network, history` (+`/api` prefix), `websocket`, `shell`, `ai_tutor` |
| 인증 | JWT(HS256) `core/security.py` + WebSocket 전용 1회용 ticket(TTL 60s, 메모리 dict) |
| DB | SQLite + SQLAlchemy async(aiosqlite), `StaticPool`, Alembic 마이그레이션(`core/db_migrations.py`, fail-closed) |
| 모델 | `MonitorSnapshot, WebUser, LoginLog, AILearningSession, AIVirtualState, AICommandAttempt, AIChatMessage, AIInteractionAudit` |
| 실시간 | `services/metrics_collector.py` 단일 수집기(5초) → `routers/websocket.py` `/ws/monitor` fan-out |
| 스케줄러 | `services/scheduler.py` APScheduler, 1분 스냅샷 저장 + 7일 보존 삭제 |
| 셸 | `routers/shell.py` — `docker run` PTY, `--network none`, `--read-only`, `--cap-drop ALL`, 사용자당 1세션/전역 5세션 |
| AI | `routers/ai_tutor.py` + `services/bedrock.py` (AWS Bedrock), `ai_rate_limit.py`, `curriculum.py`, `task_grader.py`, `virtual_linux.py` |
| 프런트 | React 18 + Vite (`frontend/src`), `api/client.js`, `context/AuthContext.jsx`, `features/{filesystem,network-diagnostics,users}` |
| 배포 | `docker-compose.yml`: frontend(nginx 80/443) / backend / docker-socket-proxy / certbot |
| CI | `.github/workflows/ci.yml` — pytest, vitest, eslint, build, compose config 검증 |

---

## 1. 커리큘럼 (M0 ~ M10)

각 모듈은 **질문 → 답변 → 판정(합격/보완/불합격)** 으로 진행한다.
판정이 "합격"이어야 다음 모듈로 넘어간다. 설명을 들은 항목은 재질문 목록에 남는다.

| # | 모듈 | 핵심 파일 | 상태 |
|---|---|---|---|
| M0 | 프로젝트 정체성 — 사용자·문제·존재 이유 | `README.md`, 라우터 전체 | 합격 (2026-09-09) |
| M1 | 부팅 시퀀스 — import → app 생성 → startup 이벤트 순서 | `backend/main.py`, `core/db_migrations.py` | 진행 중 |
| M2 | 인증 흐름 — 로그인 → JWT → 의존성 주입 → 401/403 분기 | `routers/auth.py`, `core/security.py` | 미시작 |
| M3 | REST 요청 1개 완전 추적 (`GET /api/cpu` 계열) | `routers/cpu.py`, `schemas/cpu.py` | 미시작 |
| M4 | 실시간 모니터링 — 단일 수집기 + fan-out + ticket 인증 | `services/metrics_collector.py`, `routers/websocket.py` | 미시작 |
| M5 | 웹 터미널 — PTY, Docker 격리, 세션 수명주기·정리 | `routers/shell.py`, `Dockerfile.webterm` | 미시작 |
| M6 | 데이터 계층 — SQLAlchemy async, StaticPool, Alembic, 스케줄러 보존 | `core/database.py`, `services/scheduler.py`, `migrations/` | 미시작 |
| M7 | AI 튜터 — Bedrock 호출, 레이트리밋, degrade 폴백, 채점 | `routers/ai_tutor.py`, `services/bedrock.py`, `services/task_grader.py` | 미시작 |
| M8 | 프런트엔드 계약 — apiFetch/401 처리, AuthContext, WebSocket 재연결 | `frontend/src/api/client.js`, `context/AuthContext.jsx` | 미시작 |
| M9 | 배포·네트워크 — Nginx TLS 종료, docker-socket-proxy, compose 프로필 | `docker-compose.yml`, `frontend/nginx.conf` | 미시작 |
| M10 | 종합 방어 — 장애 시나리오, 확장성, 재설계, 30초/1분/3분 답변 | 전체 | 미시작 |

**부가 트랙 (요청 시 별도 진행)**
- CS 질문 모드 (DNS, TCP/UDP, 3-way handshake, HTTP/WS 업그레이드)
- "AI로 만들었다" 방어 훈련 (CLAUDE.md §11) — 내가 직접 결정한 것 정리

---

## 2. 진도

### 완료한 주제
- **M0 — 프로젝트 정체성** (2026-09-09)
  - Q1 사용자·기능 통합 이유 → **보완** (근거 파일 없음, 시뮬레이터 2종 혼동)
  - Q2 AI 튜터의 명령 실행 위치 → **합격** (`services/virtual_linux.py`가 실행, AI는 조언만, 결과는 DB)

### 진행 중
- **M1 — 부팅 시퀀스** (`backend/main.py`)
  - Q1: import 단계에서 라우터 import가 실패하면 서버는 어떻게 되는가? → 답변 대기

### 다음 세션 시작 지점
- M1 Q1부터

## 3. 내가 약한 지점
- 답변에 파일·함수 근거를 붙이지 않고 일반론으로 설명하는 습관 (M0 Q1)
- 브라우저 시뮬레이터(`frontend/src/features/*`)와 서버 시뮬레이터(`backend/services/virtual_linux.py`) 구분

---

## 4. 재질문 목록 (설명을 들은 항목 — 나중에 각도 바꿔 재질문)
- (없음)
