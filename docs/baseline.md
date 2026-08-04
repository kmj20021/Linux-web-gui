# Phase 0 Baseline

기록 시각: 2026-07-29T17:14:45+09:00
목적: Phase 0 시작 시점의 재현 가능한 상태를 보존한다. 이 문서는 사용자 데이터,
비밀, 토큰, 사용자명, IP 주소 및 감사 로그 값을 포함하지 않는다.

## Git 상태

- Branch: `main`
- HEAD: `1241628f071e7bab44f5c5e1261f4e7664a54e32`
- `git status --short` (exit 0): 시작 전부터 `AGENTS.md` 수정, 기존 `docs/` 문서
  8개 삭제, `AGENTS2.md` 및 `docs/LEARNING_LOG.md`, `docs/evaluation.md`,
  `docs/re-plan.md` 추가가 있었다. 이 기준선 작업은 이 변경들을 수정·복원하지
  않는다.
- `git diff --check` (exit 0): 공백 오류 없음. 사용자 변경 `AGENTS.md`에 대한
  CRLF 변환 경고가 출력됐다. 전역 Git ignore 파일 접근 경고는 `git status` 실행에서
  출력됐다.
- Phase 0 산출물 생성 전 `docs/baseline.md`는 Git 추적 파일이 아니었다.

## 실행 환경

| 항목 | 결과 | 종료 코드 | 비고 |
| --- | --- | ---: | --- |
| `python --version` | Python 3.11.9 | 0 | Windows PowerShell |
| `node --version` | v20.20.2 | 0 | Windows PowerShell |
| `npm --version` | 10.8.2 | 0 | Windows PowerShell |
| `docker compose version` | Docker Compose v5.1.0 | 0 | Docker config 접근 경고가 있었지만 버전 조회는 성공 |

## 비민감 DB 상태

DB 레코드나 스키마 데이터를 열람하지 않았다.

| 경로 | 크기 | 스키마 버전 상태 |
| --- | ---: | --- |
| `backend/linux_web_gui.db` | 360,448 bytes | `backend/migrations` 아래 Alembic version artifact를 찾지 못함 |
| `data/linux_web_gui.db` | 3,256,320 bytes | `backend/migrations` 아래 Alembic version artifact를 찾지 못함 |

이는 DB 안에 버전 정보가 없다는 단정이 아니라, 파일 시스템에서 확인 가능한
버전 관리 산출물이 없다는 관찰이다. 운영 DB와 사용자 데이터에는 접근하거나
변경하지 않았다.

## 현재 검사 재현

| 명령 | 종료 코드 | 결과 |
| --- | ---: | --- |
| `python -m compileall -q main.py core routers schemas services migrations` (`backend/`) | 0 | Python 문법 컴파일 통과 |
| `python test/test_endpoints.py` (`backend/`) | 1 | 기본 실행에서 `routers` 모듈 import 실패 |
| `python test/test_websocket.py` (`backend/`) | 1 | 기본 실행에서 `routers` 모듈 import 실패 |
| `python test/test_database_integration.py` (`backend/`) | 1 | 기본 실행에서 `core` 모듈 import 실패 |
| `npm ls --depth=0` (`frontend/`) | 1 | `@xterm/xterm`, `@xterm/addon-fit`가 선언됐지만 현재 설치 상태에서 누락됨 |
| `npm run build` (`frontend/`, sandbox) | 1 | sandbox가 상위 홈 경로를 `lstat`하지 못해 실행 환경 권한 오류 |
| `npm run build` (`frontend/`, 승인된 동일 명령 재시도) | 1 | Vite/Rollup이 `src/components/Terminal.jsx`의 `@xterm/xterm` import를 resolve하지 못함 |
| `docker compose config --quiet` | 0 | config 유효. Compose의 obsolete `version` 속성 및 Docker config 접근 경고가 출력됨 |
| `git diff --check` | 0 | 공백 오류 없음 |

프론트의 `package.json`에는 현재 `lint`와 `test` 스크립트가 없다. 따라서
Phase 1 QA 작업 이전에는 해당 명령을 성공 조건으로 가정하지 않는다. `npm ci`는
기존 사용자 `node_modules`에 영향을 줄 수 있어 실행하지 않았다.

## 확정 정책 결정

| ID | 확정값 |
| --- | --- |
| DEC-01 | 사용자 ID 컬럼은 `username` 유지 |
| DEC-02 | 전역 관리자; `created_by`는 감사 정보 |
| DEC-03 | admin만 교육용 `demo-*` 자식 프로세스 종료 가능 |
| DEC-04 | 60초 이하 일회성 WebSocket ticket |
| DEC-05 | 운영 인증서 부재 시 시작 실패, HTTP는 개발 프로필만 |
| DEC-06 | 셸 네트워크 기본 `none` |
| DEC-07 | 일반 모니터링은 로그인 사용자, 연결 목록은 admin |
| DEC-08 | 원본 스냅샷 7일 후 삭제 |

## 제한사항

- 실행 중인 Linux/Raspberry Pi 호스트, 실제 Docker 셸, TLS 인증서 및 실제 WebSocket
  연결은 이 기준선에서 검사하지 않았다.
- 레거시 테스트 스크립트는 기본 실행 실패를 기록한 것이며, pytest 기반 자동 검사는
  Phase 1 QA-01의 범위다.
- 평가 문서가 보고한 추가 `PYTHONPATH` 우회 실행은 이 기준선에서 재실행하지 않았다.
  기본 실행 오류와 자동화의 부재를 먼저 비교 기준으로 고정한다.
