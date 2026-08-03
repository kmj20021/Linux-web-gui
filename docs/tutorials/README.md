# 단계별 학습 과제

이 저장소의 실제 코드로 서버·클라우드 기초를 확인하는 7단계 과제다.

## 이 문서의 규칙

**답은 쓰지 않는다.** 질문과 "어디를 보면 되는지"만 있다. 완성된 코드를 읽으면
*무엇을* 했는지는 보이지만 *왜* 그렇게 했는지는 보이지 않기 때문이다. 답을 함께
적어 두면 읽는 순간 다 아는 것 같지만 면접에서 꼬리질문에 막힌다.

**실패 테스트는 직접 작성한다.** 각 단계의 "실패 테스트"는 코드가 아니라 명세다.
먼저 그 테스트를 만들어 **실패하는 것을 눈으로 확인**하고, 그다음 통과시킨다.
이미 통과하는 코드에 테스트를 덧붙이면 그 테스트가 진짜로 무언가를 잡는지 알 수
없다. 이 프로젝트에서 실제로 발견된 권한 누락 3건은 모두 "테스트는 통과하는데
실제로는 뚫려 있던" 경우였다.

**순서를 지킨다.** 뒤 단계는 앞 단계의 개념을 전제한다.

**기록은 `docs/LEARNING_LOG.md`에 한다.** 이해도 단계(L0~L4)와 막힌 지점을 남긴다.

## 공통 준비

```bash
python -m pytest backend/tests            # 백엔드 테스트
npm --prefix frontend test -- --run       # 프런트엔드 테스트
bash scripts/gate.sh --fast               # 빠른 확인 (완료 게이트 아님)
bash scripts/gate.sh                      # 전체 검증
```

새 테스트는 `backend/tests/`에 `test_*.py`로 둔다. 기존 테스트가 좋은 본보기다.
실제 DB(`data/*.db`)나 실제 계정은 절대 테스트에 쓰지 않는다. `conftest.py`가
메모리 DB를 강제하는 이유를 1단계에서 확인하게 된다.

---

## 1단계 — REST와 Pydantic

**목표**: 요청이 함수에 도달하기 전에 무엇이 검증되는지 설명할 수 있다.

**관련 파일**
- `backend/routers/cpu.py`, `memory.py`, `disk.py` — 가장 단순한 조회 라우터
- `backend/schemas/` — 응답 모델
- `backend/main.py` — 라우터 등록과 prefix

**위험 사항**
- 응답 모델 없이 dict를 그대로 반환하면 내부 필드가 조용히 새어 나간다.
- 수집 실패를 빈 배열이나 0으로 돌려주면 "값이 0인 상태"와 구분되지 않는다.
  이 프로젝트가 DATA-01에서 503으로 바꾼 이유다.

**실패 테스트 (직접 작성)**
1. 필수 쿼리 파라미터를 빼고 호출하면 500이 아니라 **422**가 나오는지.
2. psutil 호출이 예외를 던지도록 monkeypatch 했을 때 200이 아니라 **503**이 나오고
   본문에 `error`와 `resource`가 있는지.

**완료 테스트**: `python -m pytest backend/tests/test_metric_reliability.py`

**복습 질문**
- `response_model`을 지정하면 실제로 무엇이 달라지나? 지정하지 않으면?
- 422와 400은 어떻게 다른가? 누가 422를 만드나?
- 디스크 사용률이 진짜 0%인 것과 수집에 실패한 것을 클라이언트는 어떻게 구분하나?
- `main.py`가 라우터 import를 `try/except`로 감싼 것은 어떤 위험을 만드나?

---

## 2단계 — JWT와 권한 행렬

**목표**: "로그인했다"와 "이 요청을 할 수 있다"가 왜 다른 문제인지 설명할 수 있다.

**관련 파일**
- `backend/core/security.py` — `get_current_user`, `get_current_admin`
- `backend/routers/auth.py` — 로그인
- `backend/routers/admin.py`, `network.py`, `process.py` — 권한이 갈리는 지점
- `docs/contracts/security-contract.md` — **권한 행렬 원본. 코드보다 이 표가 먼저다**
- `backend/tests/test_authorization_matrix_e2e.py` — 실제 체인 검증

**위험 사항**
- 토큰 서명만 확인하고 DB를 조회하지 않으면, 계정을 비활성화하거나 admin에서
  viewer로 강등해도 기존 토큰이 만료될 때까지 그대로 통과한다.
- 프런트엔드에서 버튼을 숨기는 것은 권한 제어가 아니다. 서버가 막지 않으면
  `curl` 한 줄로 뚫린다.
- 라우터에 의존성을 붙였다는 사실과 실제로 거부된다는 사실은 다르다. 테스트에서
  의존성을 가짜로 바꿔치기하면 앞의 것만 증명된다.

**실패 테스트 (직접 작성)**
1. viewer 토큰으로 `GET /api/network/connections`를 호출하면 **403**인지.
2. 토큰을 발급받은 뒤 그 사용자를 `is_active=False`로 바꾸고 같은 토큰으로
   보호 자원을 호출하면 **401**인지. (403이 아니어야 하는 이유를 설명할 수 있어야
   한다. 힌트는 `frontend/src/api/client.js`에 있다.)
3. 인증 헤더 없이 호출하면 **401**인지.

**완료 테스트**: `python -m pytest backend/tests/test_authorization_matrix_e2e.py`

**복습 질문**
- 401과 403은 각각 무엇을 뜻하나? 비활성 사용자는 왜 401인가?
- 로그인 실패 시 "비밀번호가 틀렸다"와 "계정이 잠겼다"를 구분해서 알려주면 어떤
  정보가 공격자에게 넘어가나?
- JWT는 서버에 저장되지 않는데, 그러면 로그아웃은 무엇을 하는 건가?
- 토큰 만료 시간을 15분으로 짧게 잡으면 무엇이 좋아지고 무엇이 불편해지나?
- 권한 검사를 각 함수 안에 `if user.role != "admin"`으로 쓰는 것과 라우터
  `dependencies=[...]`로 거는 것의 차이는? 어느 쪽이 빠뜨리기 쉬운가?

---

## 3단계 — WebSocket ticket과 로그 보안

**목표**: 자격 증명을 URL에 넣으면 안 되는 이유를 구체적인 경로로 설명할 수 있다.

**관련 파일**
- `backend/core/security.py` — `issue_ws_ticket`, `consume_ws_ticket`
- `backend/routers/websocket.py`, `backend/routers/shell.py` — 첫 메시지 인증
- `docs/contracts/security-contract.md` §3 — ticket 계약
- `backend/tests/test_websocket_authorization.py`, `test_secret_logging.py`

**위험 사항**
- `ws://host/ws/monitor?token=...`은 Nginx 액세스 로그, 브라우저 히스토리,
  리퍼러, 프록시 로그에 남는다. 로그는 보통 평문이고 오래 보관된다.
- ticket을 재사용할 수 있으면 로그를 본 사람이 그대로 연결할 수 있다.
- 예외 메시지에 토큰을 그대로 실어 로깅하면 같은 문제가 반복된다.

**실패 테스트 (직접 작성)**
1. 같은 ticket으로 두 번 연결하면 두 번째가 거부되는지.
2. `monitor` 용도로 발급한 ticket으로 `/ws/shell`에 연결하면 거부되는지.
3. 인증 메시지를 보내기 전에 데이터를 요청하면 아무것도 오지 않는지.

**완료 테스트**: `python -m pytest backend/tests/test_websocket_authorization.py backend/tests/test_secret_logging.py`

**복습 질문**
- ticket 수명을 60초로 잡은 근거는? 5초라면, 1시간이라면 무엇이 문제인가?
- ticket을 서버 메모리에 두면 backend를 2대로 늘렸을 때 무슨 일이 생기나?
- WebSocket에는 왜 `Authorization` 헤더를 쓰기 어려운가?
- 로그에 토큰이 남았는지 자동으로 확인하려면 무엇을 검사해야 하나?
  (`scripts/security_scan.py`를 보라)

---

## 4단계 — 비동기 수집과 이벤트 루프

**목표**: 어떤 코드가 이벤트 루프를 막는지 구분하고, 막지 않게 바꿀 수 있다.

**관련 파일**
- `backend/services/metrics_collector.py` — 단일 수집기와 fan-out
- `backend/services/scheduler.py` — 주기 작업
- `backend/routers/websocket.py` — 구독자
- `backend/tests/test_metrics_collector.py`

**위험 사항**
- psutil 호출은 블로킹이다. `async def` 안에서 그냥 부르면 그동안 **모든** 요청이
  멈춘다. `async`를 붙였다고 비동기가 되지 않는다.
- 연결마다 따로 수집하면 50명이 붙었을 때 같은 일을 50번 한다.
- 수집기를 종료하지 않으면 서버가 안 내려간다.

**실패 테스트 (직접 작성)**
1. 구독자를 3개 만들고 한 주기 동안 실제 수집 함수가 **1번만** 호출되는지.
2. 블로킹 함수가 `asyncio.to_thread`로 넘어가는지 (수집 중에 다른 코루틴이
   진행되는지로 확인).

**완료 테스트**: `python -m pytest backend/tests/test_metrics_collector.py`

**복습 질문**
- 이벤트 루프가 "막힌다"는 게 정확히 무슨 상태인가? 사용자에게는 어떻게 보이나?
- `asyncio.to_thread`는 무엇을 해결하고 무엇을 해결하지 못하나?
- 구독자가 0명이어도 5초마다 수집한다. 장점과 단점은?
- 수집 주기를 1초로 줄이면 어디부터 무너지나?

---

## 5단계 — SQLite migration과 보존 정책

**목표**: 운영 중인 DB의 스키마를 안전하게 바꾸는 절차를 설명하고 실행할 수 있다.

**관련 파일**
- `backend/migrations/versions/0001_initial_schema.py`
- `backend/core/db_migrations.py` — startup에서 `alembic upgrade head`
- `backend/services/scheduler.py` — 스냅샷 보존 job
- `docs/db-operations.md` — 백업·복구 절차
- `backend/tests/test_db_migrations.py`

**위험 사항**
- 코드에서 `ALTER TABLE`을 직접 실행하면 어떤 서버가 어느 스키마인지 알 수 없다.
- 마이그레이션 실패를 `except`로 삼키면 **깨진 스키마 위에서 서버가 뜬다.**
  이 프로젝트가 fail-closed를 택한 이유다.
- 보존 정책 없이 1분마다 스냅샷을 쌓으면 디스크가 조용히 찬다.
- **실제 DB로 연습하지 않는다.** 반드시 복사본으로 한다.

**실패 테스트 (직접 작성)**
1. 마이그레이션이 실패하도록 만들었을 때 앱이 뜨지 않고 종료되는지.
2. 보존 기한(7일)이 지난 원본 스냅샷만 지워지고 집계는 남는지. 경계값(정확히
   7일)에서 어떻게 되는지.

**완료 테스트**: `python -m pytest backend/tests/test_db_migrations.py`

**복습 질문**
- `alembic upgrade head`를 앱 startup에서 하는 것과 별도 명령으로 분리하는 것의
  차이는? 서버를 2대로 늘리면 어느 쪽이 문제가 되나?
- 롤백이 불가능한 마이그레이션에는 어떤 것이 있나?
- SQLite를 PostgreSQL로 바꾼다면 이 코드에서 무엇이 먼저 깨지나?

---

## 6단계 — Nginx TLS와 우회 차단

**목표**: 요청이 브라우저에서 backend까지 가는 경로와, 그 경로를 건너뛸 수 있는
구멍을 찾을 수 있다.

**관련 파일**
- `frontend/nginx.conf` (운영), `frontend/nginx-http.conf` (개발)
- `frontend/start.sh` — 인증서 확인과 도메인 치환
- `docker-compose.yml`, `docker-compose.dev.yml` — 포트 노출 범위
- `docs/operations.md` — 인증서 발급 절차

**위험 사항**
- backend 포트(8000)를 호스트에 그대로 열면 Nginx의 TLS·rate limit·보안 헤더를
  전부 우회할 수 있다. 프록시는 우회 가능하면 의미가 없다.
- 인증서가 없을 때 HTTP로 조용히 내려가면, 배포는 성공한 것처럼 보이는데 실제로는
  평문으로 서비스된다.

**실패 테스트 (직접 작성)**
1. 운영 Compose 설정에서 backend 서비스에 호스트 포트 바인딩이 **없는지**
   (`docker compose config` 출력을 파싱).
2. 인증서 파일이 없을 때 시작 스크립트가 0이 아닌 코드로 종료하는지.

**완료 테스트**: `bash scripts/gate.sh`의 compose config 검사 + 위 테스트

**복습 질문**
- TLS "종료"란 정확히 어디서 무엇이 끝나는 건가?
- 자체 서명 인증서로도 암호화는 된다. 그런데 왜 CA 발급이 필요한가?
- rate limit을 IP별로 걸면 못 막는 공격은 무엇인가?
- 개발용 HTTP 설정과 운영 설정을 한 파일에 조건문으로 두면 어떤 사고가 나나?

---

## 7단계 — Docker 셸 격리

**목표**: 컨테이너 안에서 임의 명령을 실행할 수 있게 해주면서도 호스트를 지키는
방법을, 각 옵션이 무엇을 막는지 수준까지 설명할 수 있다.

**관련 파일**
- `Dockerfile.webterm` (저장소 루트)
- `docker-compose.yml` — 셸 컨테이너 옵션
- `backend/routers/shell.py` — 세션 생성·한도·정리
- `backend/services/file_tree.py` — 경로 탈출 방지
- `backend/tests/test_shell_limits.py`, `test_shell_file_tree.py`

**위험 사항**
- Docker 소켓을 컨테이너에 마운트하면 그 컨테이너는 사실상 호스트 root다.
- 네트워크를 열어 두면 셸이 내부망 스캔이나 외부 유출 통로가 된다.
- `..`나 심볼릭 링크로 허용 루트 밖을 읽을 수 있으면 격리가 뚫린다.
- 세션 수와 자원에 한도가 없으면 셸 하나로 호스트를 마비시킬 수 있다.

**실패 테스트 (직접 작성)**
1. 허용 루트 밖으로 나가는 경로(`../../etc/passwd`, 밖을 가리키는 심볼릭 링크)가
   거부되는지.
2. 한 사용자가 두 번째 세션을 요청하면 거부되는지.
3. admin이 **다른 사용자의** 세션을 조회하거나 초기화할 수 없는지.
   (전역 관리자 정책은 사용자 관리 API에만 적용된다 — 계약 §5)

**완료 테스트**: `python -m pytest backend/tests/test_shell_limits.py backend/tests/test_shell_file_tree.py backend/tests/test_shell_rest_authorization.py`

**복습 질문**
- `cap-drop: ALL`, `no-new-privileges`, `read_only`, `network: none`은 각각 어떤
  공격을 막나? 하나만 빠지면 무엇이 가능해지나?
- 컨테이너를 non-root로 돌리는 것과 `no-new-privileges`는 왜 둘 다 필요한가?
- `os.path.join`으로 경로를 합치는 것만으로는 왜 탈출을 막을 수 없나?
- 이 셸 기능을 실제 서비스에 넣는다면, 지금 구조에서 무엇을 더 해야 하나?

---

## 마지막 점검

7단계를 마쳤다면 다음 질문에 답할 수 있어야 한다. 어느 하나라도 막히면 해당
단계로 돌아간다.

- 이 프로젝트에서 가장 위험했던 취약점은 무엇이었고, 왜 그런 코드가 나왔나?
  (`docs/evaluation.md`와 `docs/re-progress.md`의 P0·P1 항목)
- 권한 누락이 세 번 반복된 원인은 무엇이었고, 어떻게 재발을 막았나?
- 이 시스템을 사용자 1,000명 규모로 올린다면 무엇부터 깨지나?
- 지금 남아 있는 운영 제한사항은 무엇인가?
  (`docs/re-progress.md`의 Known Limitations)
