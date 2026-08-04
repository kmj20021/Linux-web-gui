# AI Linux 학습 시나리오

이 문서는 `backend/test/fixtures/ai_learning_scenarios.json`의 사람이 읽는 설명이다. 두 파일은 시나리오 ID, 문제 ID, 초기·목표 상태 및 채점 의미가 동일하다.

## 공통 실행·채점 원칙

모든 명령은 `simulation_only`이며 호스트나 Docker에서 실제로 실행하지 않는다. 채점은 특정 명령 문자열을 입력했는지가 아니라 명령 처리 후의 **최종 가상 상태**가 목표 상태를 충족하는지를 우선한다. 따라서 서로 다른 안전한 명령 순서라도 같은 목표 상태를 만들면 우회 정답(`alternative`)으로 성공 처리할 수 있다.

fixture에는 정확히 3개 시나리오와 각 2개 문제, 총 6개 문제가 있다. 문제마다 4개씩, 앞 단계 결과를 다음 단계가 이어받는 연속 상태 step을 정의하여 총 **24개**다. 모든 step은 `state_before`와 `state_after`를 가지며, 앞 step의 `state_after`는 다음 step의 `state_before`와 같다. 각 문제의 첫 `state_before`는 `initial_state`, 마지막 `state_after`는 `expected_final_state`와 같고, 각 시나리오 안에서 첫 번째 문제의 `expected_final_state`는 두 번째 문제의 `initial_state`와 같다.

## 지원 명령과 거부 문법

| 구분 | 범위 | 기대 결과 |
|---|---|---|
| 지원 | `systemctl status/start/stop/restart/enable/disable` | 가상 서비스 상태 조회·변경 |
| 지원 | `useradd/userdel/usermod/passwd` | 가상 사용자 상태 변경 |
| 지원 | `chmod/chown/ls/cat` | 가상 파일 상태 조회·변경 |
| 지원 | `ufw allow/deny/status` | 가상 방화벽 상태 조회·변경 |
| 지원 | `ss/curl/ping` | 가상 네트워크 상태 조회 |
| 지원 | 제한된 `apt install/remove` | 가상 패키지 상태 변경 |
| 거부 | `;`, `&&`, `||`, pipe(`|`) | `unsupported_syntax`, 상태 변경 없음 |
| 거부 | command substitution(`$(...)`), backtick | `unsupported_syntax`, 상태 변경 없음 |
| 거부 | redirect(`>`, `>>`, `<`, `2>`) | `unsupported_syntax`, 상태 변경 없음 |
| 거부 | 임의 셸 스크립트 | `unsupported_syntax`, 상태 변경 없음 |

거부된 입력에는 `[SIMULATION] 현재 시나리오에서 지원하지 않는 명령입니다.`를 반환하며 어떤 실제 실행도 하지 않는다.

## 시나리오와 문제

| 시나리오 ID | 문제 ID | 학습 목표 | 초기 상태 | 목표 상태 | 성공 / 부분 / 실패 |
|---|---|---|---|---|---|
| `service_recovery` | `service_recovery_01` | 중지된 Nginx 시작 | nginx 설치됨, inactive, disabled | nginx active | active / enabled만 설정 / inactive 유지 |
| `service_recovery` | `service_recovery_02` | 자동 시작 설정 | nginx active, disabled | nginx active, enabled | active+enabled / active+disabled / inactive |
| `account_permissions` | `account_permissions_01` | 배포 사용자 생성 | 사용자 없음, 설정 파일 root:root 644 | deploy 사용자 존재 | deploy 존재 / 다른 사용자 생성 시도 / deploy 없음 |
| `account_permissions` | `account_permissions_02` | 최소 파일 권한 설정 | deploy 존재, 설정 파일 root:root 644 | deploy:deploy 640 | 소유권+mode 일치 / 둘 중 하나 / 초기 유지 또는 권한 확대 |
| `remote_access_recovery` | `remote_access_recovery_01` | SSH 포트 차단 원인 진단 | SSH active·22 listen, 방화벽 22 차단, 원격 접속 차단 | listen과 차단 규칙을 확인해 원인을 방화벽으로 진단 | 두 항목과 원인 확인 / 한 항목만 확인 / 원인 미확인 또는 SSH 중지 |
| `remote_access_recovery` | `remote_access_recovery_02` | SSH 방화벽 규칙 복구 | SSH active·22 listen, 방화벽 22 차단 | SSH active, 방화벽 22 허용, 원격 접속 가능 | 허용+active+접속 가능 / 허용+inactive / 차단 유지 |

## 힌트와 답안 예시

모든 문제는 정확히 세 단계 힌트를 사용한다.

1. 개념(`concept`): 무엇을 확인하거나 바꿔야 하는지 설명한다.
2. 명령 계열(`command_family`): 사용할 명령군을 좁힌다.
3. 구문(`syntax`): 목표에 맞는 구체적인 명령 형식을 제시한다.

각 문제에는 `correct`, `partial`, `incorrect`, `alternative` 답안 예시가 모두 있다. `alternative`는 정답과 명령 문자열이나 순서가 달라도 최종 목표 상태가 같으면 성공한다는 원칙을 검증한다. `chmod 777`, 사용자 삭제, 서비스 중지, 방화벽 차단 및 패키지 제거처럼 위험하거나 장애를 만드는 예시도 오직 fixture의 `simulation_only` 데이터이며 실행 대상이 아니다.

## 연속 상태 fixture

| step | 문제 | 상태 흐름 요약 |
|---:|---|---|
| 1–4 | `service_recovery_01` | inactive 확인 → 시작 → active 확인 → HTTP 확인 |
| 5–8 | `service_recovery_02` | disabled 확인 → enable → restart → active/enabled 확인 |
| 9–12 | `account_permissions_01` | 파일 확인 → deploy 생성 → 암호 상태 설정 → 파일 불변 확인 |
| 13–16 | `account_permissions_02` | 소유권 변경 → mode 640 → 상태 확인 → 읽기 정책 확인 |
| 17–20 | `remote_access_recovery_01` | SSH active 확인 → 22 listen 확인 → 방화벽 차단 확인 → 차단 원인 확정 |
| 21–24 | `remote_access_recovery_02` | 22 차단 재확인 → 22 허용·접속 복구 → listen 확인 → 허용 규칙 확인 |

세 번째 시나리오에서 `ufw deny 22/tcp`나 `systemctl stop ssh`는 원격 서버의 관리 접속을 끊을 수 있는 위험을 학습하기 위한 오답 예시일 뿐이며 실제로 실행하지 않는다. 위 흐름 전체는 실제 Linux 명령 실행 절차가 아니라 향후 상태 엔진과 채점 테스트가 읽을 결정적 입력·기대값이다.
