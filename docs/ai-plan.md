# Amazon Bedrock 기반 Linux 학습 AI 통합 계획

작성일: 2026-07-21  
대상 프로젝트: Linux Web GUI  
문서 상태: 구현 전 계획

## 1. 목표

기존 Linux Web GUI의 Docker 터미널에 Amazon Bedrock 기반 학습 도우미를 결합한다. 학습자는 실제 Docker 환경에서 안전한 명령을 실행하고, 실제 실행이 어렵거나 위험한 관리자 명령은 상태 기반 AI 시뮬레이션 환경에서 학습한다.

사용자 화면에는 터미널을 두 개 배치하지 않는다. 기존 터미널 UI 하나를 유지하고 상단의 명시적인 모드 전환 버튼으로 실행 환경을 선택하게 한다.

```text
[실제 Docker 실습] [AI 서버 시뮬레이션]

┌──────────────────────────────────────┬─────────────────────────┐
│ 하나의 터미널 UI                       │ AI 학습 도우미          │
│                                      │                         │
│ user@linux:~$                        │ 현재 문제               │
│                                      │ 힌트 및 명령 설명       │
│                                      │ 학습 진행 상태          │
└──────────────────────────────────────┴─────────────────────────┘
```

### 1.1 AWS 운영 전제

이 프로젝트는 개인 AWS 계정이 아니라 학교에서 제공하는 관리형 AWS 계정과 기존 서버를 사용한다. 개발자가 IAM 역할 생성, 정책 변경, 모델 구독 또는 Organizations 정책을 직접 변경할 수 있다고 가정하지 않는다. 필요한 AWS 작업은 학교 관리자에게 목적과 최소 권한을 제시하여 요청한다.

현재 프로젝트는 EC2에서 Docker Compose로 React/Nginx와 FastAPI를 실행하는 웹 서비스다. `aws_ref.md`의 Polylog 앱에서 사용한 Lambda, API Gateway, SAM, 이미지 OCR, S3 업로드, Translate 및 Comprehend 구조는 이번 MVP에 적용하지 않는다. 재사용하는 내용은 Bedrock 모델 접근, 리전, IAM, 오류 처리, 출력 검증, 쿼터 및 비용 관리 경험이다.

Bedrock 구현을 시작하기 전에 관리자로부터 다음 정보를 먼저 받아야 한다.

- 사용할 AWS 계정과 Bedrock 리전
- 학교에서 허용한 모델 또는 inference profile ID
- FastAPI 백엔드가 사용할 실제 IAM principal
- 허용된 cross-region 처리 범위
- 요청량, 비용 및 로그 보존 정책

## 2. 핵심 설계 결정

1. Docker 컨테이너는 현재처럼 사용자당 최대 1개만 사용한다.
2. AI 시뮬레이터를 위한 두 번째 컨테이너는 만들지 않는다.
3. 실제 모드와 시뮬레이션 모드는 같은 터미널 UI를 재사용한다.
4. MVP에서는 사용자가 모드를 직접 선택한다. 명령어에 따른 자동 모드 전환은 하지 않는다.
5. 실제 Linux 상태와 가상 Linux 상태는 서로 독립적으로 관리한다.
6. 가상 상태의 최종 결정권은 Bedrock이 아니라 백엔드 상태 엔진이 가진다.
7. Bedrock은 문제 설명, 단계별 힌트, 결과 해설 및 학습자 수준 조정을 담당한다.
8. 성공 여부는 가능한 한 규칙 기반 채점기로 판정한다.
9. AI 시뮬레이션 출력에는 항상 `SIMULATION` 표시를 제공한다.

## 3. 전체 구조

```text
React Terminal 페이지
├── 실제 Docker 실습 모드
│   └── /ws/shell
│       └── FastAPI DockerSession
│           └── webterm 컨테이너 1개
│
├── AI 서버 시뮬레이션 모드
│   └── /api/ai/sessions/{id}/commands
│       └── 명령 파서 및 허용 목록
│           └── 가상 상태 엔진
│               ├── DB 상태 조회·변경
│               └── 규칙 기반 성공 판정
│
└── AI 학습 도우미 패널
    └── /api/ai/sessions/{id}/chat
        └── Bedrock 서비스
            ├── 학습자 수준
            ├── 현재 문제
            ├── 최근 시도 결과
            └── 가상 상태 요약
```

현재 구현 중 재사용할 부분은 다음과 같다.

- `frontend/src/pages/Terminal.jsx`: 터미널 페이지와 화면 분할 구조
- `frontend/src/components/Terminal.jsx`: xterm.js 입력 및 출력 처리
- `backend/routers/shell.py`: JWT 인증, WebSocket 및 사용자별 Docker 세션
- `backend/core/models.py`: SQLAlchemy 모델 패턴
- `backend/core/security.py`: JWT 사용자 인증
- `Dockerfile.webterm`: 실제 실습용 Ubuntu 이미지

## 4. 사용자 경험

### 4.1 실제 Docker 실습 모드

기존 터미널과 동일하게 동작한다. 사용자가 입력한 문자는 WebSocket을 통해 Docker 컨테이너의 PTY로 전달된다.

대상 예시:

- `mkdir`, `touch`, `cp`, `mv`
- `cat`, `grep`, `find`, `awk`, `jq`
- `chmod`, 일반 사용자가 소유한 파일의 `chown`
- `ps`, `kill`, `curl`, `ping`
- 파이프, 리다이렉션, 셸 스크립트

실제 파일·프로세스 상태를 확인할 수 있으므로 출력과 exit code를 그대로 학습한다.

### 4.2 AI 서버 시뮬레이션 모드

사용자가 입력한 명령을 Docker에 전달하지 않는다. FastAPI가 명령을 분석하고 DB에 저장된 가상 서버 상태를 읽어 결과를 계산한다. Bedrock은 계산된 결과를 터미널 형태로 표현하고 교육적 설명을 생성한다.

대상 예시:

- `sudo systemctl stop ssh`
- `sudo systemctl restart nginx`
- `sudo useradd`, `sudo userdel`
- `sudo ufw deny 22`
- `sudo iptables -F`
- 시스템 설정 파일 삭제 및 복구
- 패키지 설치·제거
- 종료, 재부팅 및 디스크 관련 명령의 영향 학습

화면은 다음처럼 실제 환경과 명확하게 구분한다.

```text
[SIMULATION] root@training-server:~# systemctl stop ssh
[SIMULATION] SSH 서비스가 중지되었습니다.
```

### 4.3 모드 전환

- 모드 전환은 터미널 상단 토글 버튼으로 수행한다.
- 전환 전 확인 메시지로 두 환경의 상태가 독립적임을 알린다.
- 모드별 명령 이력과 화면 버퍼를 분리한다.
- 시뮬레이션 모드는 테두리 색상과 배지를 다르게 표시한다.
- 실제 모드의 파일이 시뮬레이션 모드에 자동으로 존재하는 것처럼 표현하지 않는다.

## 5. AI 학습 흐름

```text
사전 진단
  → 초급·중급·고급 수준 결정
  → 수준에 맞는 시나리오 및 문제 제시
  → 학습자 명령 입력
  → 실제 실행 또는 가상 상태 변경
  → 규칙 기반 채점
  → Bedrock이 결과를 설명
  → 요청 시 단계별 힌트 제공
  → 시도 이력 저장
  → 다음 문제 또는 난이도 결정
```

힌트는 정답을 즉시 제공하지 않고 다음 세 단계로 구성한다.

1. 개념 힌트: 확인해야 할 Linux 개념 설명
2. 명령 계열 힌트: 사용할 명령 또는 옵션 종류 안내
3. 구문 힌트: 정답 명령의 일부 제공

## 6. 상태 관리 원칙

전체 채팅 기록을 매번 Bedrock에 전달하는 방식은 사용하지 않는다. 대화 내용과 서버 상태를 분리하고, 요청마다 필요한 정보만 구성한다.

### 6.1 사실 정보

백엔드 상태 엔진이 소유한다.

- 사용자와 그룹
- 파일 및 디렉터리
- 소유자와 권한
- 서비스 실행·활성화 상태
- 프로세스
- 설치 패키지
- 방화벽 규칙
- 열린 포트
- 디스크 및 마운트 상태

### 6.2 학습 정보

- 진단 수준
- 현재 커리큘럼과 문제
- 명령 시도 횟수
- 성공·실패 결과
- 힌트 사용 단계
- 문제별 소요 시간
- 완료한 학습 항목

### 6.3 대화 정보

- 사용자 질문
- AI 답변
- 메시지 생성 시각
- 관련 문제와 명령 시도 ID
- 사용한 Bedrock 모델
- 입력·출력 토큰 수 또는 호출 비용 산정 정보

Bedrock 요청에는 다음 정보만 전달한다.

```text
시스템 학습 규칙
+ 학습자 수준
+ 현재 문제
+ 현재 가상 상태 요약
+ 직전 명령 및 규칙 기반 판정 결과
+ 최근 대화 일부 또는 대화 요약
```

## 7. 데이터베이스 계획

기존 SQLite와 비동기 SQLAlchemy 패턴을 우선 사용한다.

### 7.1 `ai_learning_sessions`

| 필드 | 설명 |
|---|---|
| `id` | 학습 세션 ID |
| `user_id` | `web_users` 참조 |
| `mode` | `docker` 또는 `simulation` |
| `level` | `beginner`, `intermediate`, `advanced` |
| `scenario_key` | 현재 시나리오 |
| `task_key` | 현재 문제 |
| `status` | 진행 중, 완료, 중단 |
| `started_at` | 시작 시각 |
| `completed_at` | 완료 시각 |

### 7.2 `ai_virtual_states`

| 필드 | 설명 |
|---|---|
| `id` | 상태 ID |
| `session_id` | 학습 세션 참조 |
| `state_json` | 가상 파일·서비스·사용자·네트워크 상태 |
| `version` | 상태 변경 순서 및 동시성 제어 |
| `updated_at` | 마지막 갱신 시각 |

초기 구현에서는 JSON 컬럼으로 시작하고, 조회나 통계가 필요한 항목만 이후 별도 테이블로 분리한다.

### 7.3 `ai_command_attempts`

| 필드 | 설명 |
|---|---|
| `id` | 시도 ID |
| `session_id` | 학습 세션 참조 |
| `mode` | 실제 또는 시뮬레이션 |
| `command_text` | 학습자가 입력한 명령 |
| `result_code` | 성공, 실패, 미지원, 차단 |
| `output_text` | 사용자에게 표시한 출력 |
| `state_before` | 변경 전 상태 요약 |
| `state_after` | 변경 후 상태 요약 |
| `is_task_success` | 문제 성공 여부 |
| `created_at` | 실행 시각 |

### 7.4 `ai_chat_messages`

| 필드 | 설명 |
|---|---|
| `id` | 메시지 ID |
| `session_id` | 학습 세션 참조 |
| `role` | `user`, `assistant`, `system` |
| `content` | 채팅 내용 |
| `attempt_id` | 관련 명령 시도 |
| `created_at` | 생성 시각 |

## 8. 백엔드 모듈 계획

```text
backend/
├── routers/
│   └── ai_tutor.py          # 세션·채팅·명령·힌트 API
├── schemas/
│   └── ai_tutor.py          # 요청 및 응답 DTO
├── services/
│   ├── bedrock.py           # Bedrock 호출 및 응답 검증
│   ├── command_parser.py     # 시뮬레이션 명령 파싱
│   ├── virtual_linux.py      # 가상 상태 조회 및 변경
│   ├── task_grader.py        # 규칙 기반 문제 채점
│   └── curriculum.py         # 문제·난이도·힌트 정책
└── core/
    └── models.py             # AI 학습 관련 테이블 추가
```

### 8.1 API 초안

| Method | 경로 | 기능 |
|---|---|---|
| `POST` | `/api/ai/sessions` | 학습 세션 생성 및 진단 시작 |
| `GET` | `/api/ai/sessions/{id}` | 진행 상태 조회 |
| `POST` | `/api/ai/sessions/{id}/commands` | 시뮬레이션 명령 실행 |
| `POST` | `/api/ai/sessions/{id}/chat` | AI 질문 및 답변 |
| `POST` | `/api/ai/sessions/{id}/hints` | 다음 단계 힌트 요청 |
| `POST` | `/api/ai/sessions/{id}/grade` | 현재 문제 채점 |
| `POST` | `/api/ai/sessions/{id}/reset` | 가상 상태 초기화 |
| `GET` | `/api/ai/sessions/{id}/history` | 명령·채팅 학습 이력 조회 |

모든 API는 JWT 사용자와 세션 소유자가 일치하는지 확인한다.

## 9. 학교 관리형 AWS 환경의 Bedrock 연동 계획

### 9.1 호출 경로와 인증

```text
브라우저
  → Nginx
  → FastAPI 백엔드 컨테이너
  → 학교가 승인한 IAM 실행 주체의 임시 자격 증명
  → Bedrock Runtime
```

- Bedrock은 FastAPI 백엔드에서만 호출한다.
- React 코드, Git 저장소, DB 및 `.env`에 장기 Access Key를 저장하지 않는다.
- 권장 방식은 관리자가 기존 EC2에 Bedrock 호출용 instance profile을 연결하거나 기존 역할에 최소 권한을 추가하는 것이다.
- 학교가 별도의 workload role 또는 임시 자격 증명 방식을 지정하면 그 방식을 따른다.
- 백엔드 컨테이너에서 실제로 인식되는 IAM principal을 STS로 확인한다. 콘솔 또는 CloudShell 사용자의 성공을 백엔드 권한 검증으로 대신하지 않는다.
- EC2 리전과 Bedrock 리전이 같다고 가정하지 않는다. Bedrock Runtime 클라이언트에 `BEDROCK_REGION`을 명시한다.
- Docker 컨테이너가 EC2의 임시 자격 증명을 안전하게 받을 수 있는지는 관리자의 IMDS 및 네트워크 정책으로 확인한다.

### 9.2 모델과 리전 결정

모델 ID를 코드에서 먼저 결정하지 않는다. 관리자가 계정 정책, 지원 리전, 사용 가능 모델, 데이터 처리 범위 및 비용을 확인한 뒤 승인한 값을 사용한다.

함께 검증할 항목:

- 모델이 승인된 Bedrock 리전에서 사용 가능한지
- foundation model ID 직접 호출인지 inference profile 호출인지
- inference profile의 source 및 destination region
- destination model ARN이 IAM, permission boundary 및 SCP에서 허용되는지
- third-party 모델의 Marketplace 구독 또는 최초 사용 절차가 완료됐는지
- Anthropic 모델이라면 계정 수준의 최초 사용 양식 제출이 완료됐는지

MVP에는 한 개의 텍스트 모델만 사용한다. 빠른 분류용 모델과 설명 생성용 모델을 나누는 것은 정확도와 비용 데이터가 확보된 뒤 확장한다.

### 9.3 환경 설정

```text
BEDROCK_ENABLED=true
BEDROCK_REGION=<관리자가 승인한 리전>
BEDROCK_MODEL_ID=<관리자가 승인한 model 또는 profile ID>
BEDROCK_MAX_TOKENS=1024
BEDROCK_TEMPERATURE=0.1
BEDROCK_CONNECT_TIMEOUT_SECONDS=3
BEDROCK_READ_TIMEOUT_SECONDS=20
BEDROCK_MAX_ATTEMPTS=2
```

- 모델 ID와 리전은 secret이 아니지만 환경별 설정으로 분리한다.
- AWS 자격 증명 환경 변수는 계획에 포함하지 않는다.
- 출력 형식이 중요한 명령 설명과 힌트 생성에는 낮은 temperature를 사용한다.
- 추후 창의적 설명이 필요하면 기능별 temperature를 분리한다.

### 9.4 API와 SDK

MVP에서는 Python `boto3`와 Bedrock Runtime의 Converse API를 사용한다. 별도의 자율 에이전트 서비스, Lambda 및 API Gateway는 도입하지 않는다.

필요한 작업:

- `backend/requirements.txt`에 검증된 `boto3` 버전을 고정
- 해당 SDK 버전이 선택 모델과 Converse API를 지원하는지 확인
- connect timeout, read timeout 및 표준 retry 설정
- `ThrottlingException`과 일시적 5xx에만 제한된 재시도 적용
- `AccessDeniedException`과 payload `ValidationException`은 재시도하지 않음
- FastAPI 요청 한 건에서 Bedrock 호출을 원칙적으로 한 번으로 제한
- 20초 내 응답하지 못하면 규칙 기반 폴백을 반환하고 UI에 제한 상태 표시

Lambda와 API Gateway가 없으므로 `aws_ref.md`의 29~30초 Gateway 제한은 직접 적용되지 않는다. 대신 다음 순서로 시간 예산을 둔다.

```text
Bedrock SDK read timeout
  < FastAPI 요청 timeout
  < Nginx proxy timeout
  < 브라우저 요청 timeout
```

### 9.5 오류 처리와 관측성

Bedrock 실패를 빈 문자열이나 정상 답변처럼 숨기지 않는다. 사용자에게는 안전한 기본 설명을 반환하되 다음 상태를 함께 전달한다.

```json
{
  "degraded": true,
  "reason": "bedrock_timeout",
  "retryable": true,
  "message": "AI 설명을 불러오지 못해 규칙 기반 안내를 제공합니다."
}
```

애플리케이션 로그에는 다음을 구조화하여 남긴다.

- AWS 오류 코드
- AWS request ID
- Bedrock 리전
- model 또는 profile ID
- 호출 기능명
- 소요 시간
- 재시도 횟수
- 폴백 발생 여부

JWT, AWS 자격 증명, 원문 프롬프트 전체, 학생 개인정보는 로그에 남기지 않는다. 학교 계정에서 Bedrock model invocation logging이 활성화되어 있는지도 관리자에게 확인한다. 활성화되어 있다면 프롬프트와 응답의 저장 위치, 접근 권한 및 보존 기간을 연구 데이터 정책과 맞춘다.

측정할 운영 지표:

- 호출 수와 성공률
- 응답 지연 p50 및 p95
- `AccessDeniedException`, throttle 및 timeout 횟수
- 입력·출력 토큰 수
- 규칙 기반 폴백 비율
- 사용자 또는 학습 세션당 추정 비용

### 9.6 모델 출력 검증과 역할 제한

Bedrock은 다음 동작을 직접 수행할 수 없다.

- Docker 명령 실행
- 호스트 파일 읽기·쓰기
- 임의 SQL 실행
- 가상 상태 직접 저장
- 문제 성공 여부 최종 확정

Bedrock이 생성한 결과는 Pydantic 스키마로 검증하고 허용된 필드만 사용한다. JSON 앞뒤에 코드펜스나 설명이 붙는 경우를 고려하되, 파싱에 실패하면 빈 값을 신뢰하지 않고 규칙 기반 폴백으로 전환한다.

검증 항목:

- 필수 필드 존재 여부
- 문자열 길이 상한
- `hint_level` 값의 범위
- enum 값
- 현재 문제와 관련 없는 명령 또는 경로 제안 여부
- 모델이 생성한 명령이 자동으로 실행되지 않는지

예상 응답 형식:

```json
{
  "terminal_output": "Failed to stop ssh.service: Unit ssh.service not loaded.",
  "explanation": "현재 시나리오의 서비스 이름은 sshd입니다.",
  "hint_level": 1,
  "suggested_concept": "systemd 서비스 이름 확인"
}
```

## 10. 가상 Linux 상태 엔진

순수 LLM이 이전 대화를 기억해 상태를 추측하게 하지 않는다. 명령 파서와 상태 전이 규칙을 코드로 구현한다.

예시:

```text
초기 상태: nginx=active
입력: sudo systemctl stop nginx
파서 결과: action=stop, resource=nginx
상태 전이: nginx active → inactive
채점 결과: 서비스 중지 성공
Bedrock 역할: 결과 출력과 위험·복구 방법 설명
```

지원하지 않는 명령은 임의 결과를 생성하지 않는다.

```text
[SIMULATION] 현재 시나리오에서 지원하지 않는 명령입니다.
사용 가능한 명령 범위를 확인하거나 힌트를 요청하십시오.
```

명령 파서는 다음 항목을 우선 지원한다.

- `systemctl status|start|stop|restart|enable|disable`
- `useradd`, `userdel`, `usermod`, `passwd`
- `chmod`, `chown`, `ls`, `cat`
- `ufw allow|deny|status`
- `ss`, `curl`, `ping`
- 제한된 `apt install|remove`

셸 확장, 임의 스크립트, 복잡한 파이프는 시뮬레이션 MVP 범위에서 제외한다.

## 11. 커리큘럼 및 시나리오

### 11.1 Nginx 장애 대응

- 서비스 상태 확인
- 설정 오류 확인
- 포트 확인
- 서비스 재시작
- 잘못된 설정 파일 복구

### 11.2 사용자와 권한 관리

- 사용자·그룹 생성
- 파일 소유자 및 권한 설정
- 과도한 권한의 위험 확인
- 사용자 삭제 전 영향 확인

### 11.3 방화벽과 원격 접속 장애

- 열린 포트 확인
- SSH 포트 차단 시뮬레이션
- 방화벽 규칙 확인 및 복구
- 원격 서버에서 접속 경로를 차단하는 위험 학습

MVP는 시나리오 3개, 시나리오별 문제 2개, 총 6개 문제를 목표로 한다.

## 12. 프론트엔드 변경 계획

```text
frontend/src/
├── pages/Terminal.jsx
├── components/
│   ├── Terminal.jsx
│   ├── TerminalModeSwitch.jsx
│   ├── AiTutorPanel.jsx
│   ├── LearningTask.jsx
│   └── HintPanel.jsx
├── api/
│   └── aiTutor.js
└── styles/
    └── AiTutor.css
```

주요 변경:

1. 터미널 상단에 실제·시뮬레이션 모드 전환 버튼 추가
2. 시뮬레이션 모드에서는 xterm 입력을 Docker WebSocket으로 보내지 않음
3. 명령 한 줄을 AI 명령 API에 전송하고 결과를 xterm에 출력
4. 오른쪽 AI 패널에 현재 문제·힌트·채팅·진행률 표시
5. 실제 모드와 시뮬레이션 모드의 화면 버퍼 분리
6. 모바일 또는 좁은 화면에서는 AI 패널을 접을 수 있도록 구성

## 13. 권한과 보안

현재 `/ws/shell`은 `admin`만 접근할 수 있다. 학생 대상 사용 전 다음 중 하나를 적용한다.

- 권장: `learner` 역할을 추가하고 격리된 터미널과 AI 학습 API만 허용
- 제한적 실험: 별도의 실험용 관리자 계정을 발급하되 운영 기능 접근은 차단

추가 보안 요구사항:

- 명령어 자동 분기 금지 및 사용자 선택 모드 사용
- AI 시뮬레이션 입력을 실제 셸에 전달하지 않음
- 명령 허용 목록과 인자 검증 적용
- Bedrock 응답을 명령으로 재실행하지 않음
- JWT 전체 값과 AWS 자격 증명을 로그에 남기지 않음
- 채팅에 포함된 비밀번호, 토큰 및 개인정보를 저장하지 않도록 필터링
- 연구 참여자의 채팅·명령 기록에 익명 식별자 사용
- 데이터 보관 기간과 삭제 정책 명시

학교 AWS 계정 관련 요구사항:

- IAM 역할과 정책은 학교 관리자가 생성 또는 변경
- 개인 장기 Access Key 발급을 요청하지 않음
- 승인된 model/profile 이외의 모델 호출 차단
- cross-region inference 사용 시 데이터 처리 리전 사전 승인
- backend 컨테이너의 실제 IAM principal로 smoke test 수행
- Bedrock 권한 거부, throttle 및 timeout을 정상적인 서비스 상태로 처리

## 14. 학교 AWS 관리자 요청 사항

### 14.1 필수 요청

| 구분 | 관리자에게 요청할 내용 | 이유 |
|---|---|---|
| 실행 주체 | FastAPI backend 컨테이너가 사용할 EC2 instance role 또는 학교 지정 workload role 확인 | 콘솔 사용자가 아닌 실제 서비스 권한으로 Bedrock을 호출하기 위해 필요 |
| 모델 | 한국어 텍스트 대화와 Converse API를 지원하는 모델 또는 inference profile 1개 승인 | 모델 ID를 임의로 정하지 않고 학교 정책과 가용 모델을 따르기 위함 |
| 리전 | `BEDROCK_REGION`, profile source/destination region 및 cross-region 허용 여부 제공 | 모델 접근 실패와 데이터 리전 문제 방지 |
| 모델 활성화 | Marketplace 구독, 모델 availability, 필요 시 Anthropic 최초 사용 절차 완료 | IAM이 있어도 모델 활성화가 안 되면 호출할 수 없음 |
| 호출 권한 | 실제 실행 역할에 `bedrock:InvokeModel` 허용 | Converse 비스트리밍 호출에 필요한 핵심 권한 |
| 리소스 범위 | 승인 profile ARN과 profile이 라우팅하는 destination foundation model ARN 허용 | 최소 권한과 cross-region profile 호출을 동시에 만족 |
| 조직 정책 | permission boundary와 Organizations SCP에서 호출 리전 및 destination region 허용 | 역할 정책만 추가해도 explicit deny가 남을 수 있음 |
| 자격 증명 전달 | backend Docker 컨테이너가 역할의 임시 자격 증명을 안전하게 사용할 수 있도록 구성 | Access Key를 파일에 저장하지 않기 위함 |
| 네트워크 | backend에서 승인 Bedrock Runtime endpoint로 HTTPS 443 통신 허용 | 제한된 학교 VPC 또는 egress 정책에서 호출하기 위해 필요 |
| 쿼터 | 승인 모델의 RPM, TPM 및 동시 호출 쿼터 확인 | 실험 중 throttle과 사용자 간 간섭 방지 |
| 비용 | 프로젝트 사용 한도, 예산 알림 기준 및 비용 확인 담당자 지정 | 학교 공용 계정의 예상치 못한 비용 방지 |
| 로그·데이터 | model invocation logging 활성화 여부, 저장 위치, 접근자 및 보존 기간 제공 | 학생 채팅과 연구 데이터의 저장 범위 확인 |

스트리밍 응답을 MVP에 사용하지 않으므로 `bedrock:InvokeModelWithResponseStream`은 처음부터 요청하지 않는다. 추후 스트리밍 UI를 구현할 때 별도로 요청한다.

관리자에게 전달할 최소 정책의 형태는 다음과 같다. 아래 ARN은 그대로 사용하지 않고 관리자가 승인한 profile과 destination model ARN으로 교체한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeApprovedBedrockModel",
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": [
        "<approved-inference-profile-arn>",
        "<destination-foundation-model-arn-1>",
        "<destination-foundation-model-arn-2>"
      ]
    }
  ]
}
```

foundation model을 직접 호출하는 경우에는 승인된 foundation model ARN만 사용한다. profile을 호출하는 경우에는 profile과 실제로 라우팅될 수 있는 destination model을 함께 허용하고 SCP의 destination region 제한도 확인한다. 학교 정책상 초기 PoC에 `Resource: "*"`만 허용할 수 있다면 관리자가 기간과 사용 주체를 제한하고, smoke test 후 가능한 리소스 범위로 축소한다.

### 14.2 관리자가 직접 처리하거나 결과를 제공할 항목

- 대상 계정과 리전에서 모델 availability 확인
- 정확한 foundation model 또는 inference profile ID 제공
- inference profile의 destination model 목록 확인
- Marketplace 구독과 third-party 모델 최초 사용 절차 처리
- 실행 역할에 정책 연결
- SCP와 permission boundary의 리전 제한 확인
- backend 컨테이너의 임시 자격 증명 접근 방식 확인
- 모델 호출 쿼터와 비용 정책 제공

개발자에게 진단용 조회 권한을 부여할 수 없다면 관리자가 위 결과를 문서 또는 화면 캡처로 제공한다.

개발자에게 제한된 진단 권한을 줄 수 있다면 다음 조회 작업만 별도로 요청한다.

- 현재 실행 주체 확인
- foundation model 목록과 계정 가용성 조회
- 승인 inference profile과 destination model 조회
- Bedrock 호출 지표 조회

리소스 생성, IAM 정책 변경 및 Marketplace 구독 권한은 진단 권한에 포함하지 않는다.

### 14.3 선택 요청

운영 관측이 필요할 때만 다음을 추가로 협의한다.

- CloudWatch에서 Bedrock 호출 지표 조회 권한
- 애플리케이션 로그 중앙 수집과 보존 기간
- 프로젝트 비용 구분을 위한 application inference profile 또는 비용 태그
- 사용량 급증 알림과 예산 알림 수신자
- 장애 시 사용할 두 번째 승인 모델 또는 profile

### 14.4 관리자 전달용 요청문

```text
제목: Linux 학습 웹 프로젝트 Amazon Bedrock 사용 권한 요청

목적:
기존 EC2 Docker Compose 기반 Linux 학습 웹 서비스의 FastAPI backend에서
학습 문제 설명과 단계별 힌트를 생성하기 위해 Amazon Bedrock을 사용하려 합니다.
AI가 실제 명령을 실행하지 않으며, 가상 Linux 상태 변경과 성공 판정은 애플리케이션 코드가 담당합니다.

요청 사항:
1. 학교 계정에서 사용 가능한 한국어 텍스트 모델 또는 inference profile 1개와 BEDROCK_REGION 제공
2. 필요 시 Marketplace 구독 및 third-party 모델 최초 사용 절차 처리
3. 실제 FastAPI backend가 사용하는 EC2 instance role 또는 workload role 확인
4. 해당 역할에 bedrock:InvokeModel 최소 권한 부여
5. inference profile 사용 시 profile과 모든 destination model 및 region을 IAM/SCP에서 허용
6. backend Docker 컨테이너가 장기 Access Key 없이 임시 자격 증명을 사용하도록 구성 확인
7. Bedrock Runtime HTTPS 통신 가능 여부 확인
8. 모델 RPM/TPM 쿼터, 프로젝트 비용 한도 및 로그 보존 정책 제공

예상 사용:
- 텍스트 입력과 텍스트 출력만 사용
- 요청당 최대 출력 1,024 tokens
- temperature 0.1
- FastAPI 요청당 원칙적으로 1회 호출
- 사용자 수와 예상 호출량은 실험 참가자 및 문제 수 확정 후 별도 전달

보안 및 데이터:
- AWS 자격 증명을 프론트엔드와 DB에 저장하지 않음
- JWT, 비밀번호, 토큰 및 개인정보를 Bedrock 입력과 애플리케이션 로그에서 제외
- 모델 출력은 Pydantic으로 검증하며 자동 명령 실행에 사용하지 않음

관리자께서 제공해 주실 값:
- 실행 role ARN
- BEDROCK_REGION
- BEDROCK_MODEL_ID 또는 inference profile ID
- 허용 destination region
- invocation logging 활성화 여부와 보존 정책
- RPM/TPM 및 비용 한도
```

### 14.5 요청하지 않는 서비스

Polylog 앱과 달리 현재 웹 MVP에서는 다음 권한을 요청하지 않는다.

- Lambda 및 API Gateway
- S3 이미지 업로드
- Textract
- Translate 및 Comprehend
- Cognito 및 CloudFront
- DynamoDB
- Step Functions 및 SQS
- IAM 역할 생성 권한
- Marketplace 구독 권한을 개발자 개인에게 직접 부여하는 것

## 15. 테스트 계획

### 15.1 테스트 원칙

- 저장소의 기존 방식에 맞춰 테스트는 `backend/test/test_<area>.py` 실행 스크립트로 작성한다.
- 기본 테스트는 실제 Bedrock을 호출하지 않는다. Bedrock 응답과 AWS 오류는 mock으로 재현한다.
- 실제 Bedrock 테스트는 `RUN_BEDROCK_LIVE=1`을 명시한 경우에만 수행한다.
- 테스트 DB는 운영 SQLite 파일과 분리한다.
- 상태 엔진과 채점기는 Bedrock 없이도 전부 테스트할 수 있어야 한다.
- 모델 출력은 항상 검증 대상이며 테스트 정답으로 사용하지 않는다.
- 모든 테스트는 성공뿐 아니라 권한 거부, timeout, 잘못된 입력과 중복 요청을 포함한다.

### 15.2 테스트 파일 계획

| 파일 | 검증 범위 |
|---|---|
| `backend/test/test_ai_models.py` | 새 SQLAlchemy 모델, 기본값, 관계, JSON 저장 및 세션 복원 |
| `backend/test/test_virtual_linux.py` | 명령 파싱, 허용 목록, 상태 전이, 미지원 문법 거부 |
| `backend/test/test_task_grader.py` | 문제별 성공·실패 판정과 힌트 단계 |
| `backend/test/test_ai_api.py` | JWT, 세션 소유권, 요청 검증, API 응답 구조 |
| `backend/test/test_bedrock_service.py` | mock Bedrock 정상 응답, 오류 분류, retry와 폴백 |
| `backend/test/test_bedrock_live.py` | 승인 role·region·model/profile의 실제 Converse 호출 |
| `backend/test/test_ai_security.py` | 명령 주입, 프롬프트 주입, 사용자 격리, 민감정보 로그 차단 |

프론트엔드는 자동 테스트 프레임워크를 새로 추가하지 않고 `npm run build`와 아래 수동 E2E 체크리스트로 검증한다. 일정이 남으면 Vitest와 React Testing Library 도입을 후속 작업으로 둔다.

### 15.3 기존 기능 회귀 테스트

AI 코드를 추가하기 전에 다음 결과를 기준선으로 기록하고, 최종 단계에서 같은 명령을 다시 실행한다.

```text
cd backend
python test/test_endpoints.py
python test/test_websocket.py

cd frontend
npm run build
```

수동 기준선:

- 로그인과 로그아웃
- 대시보드 모니터링 WebSocket
- 실제 Docker 터미널 연결
- 파일 생성 후 파일 탐색기 반영
- 터미널 초기화와 재연결

AI 구현 후 기존 기능에서 새 오류가 하나라도 발생하면 완료로 처리하지 않는다.

### 15.4 DB 테스트

필수 테스트:

1. 학습 세션 생성 시 초기 수준, 시나리오와 상태가 저장된다.
2. 채팅과 명령 시도가 올바른 사용자·세션에 연결된다.
3. 새로고침 또는 재로그인 후 진행 상태가 복원된다.
4. 한 사용자가 다른 사용자의 세션을 조회하거나 변경할 수 없다.
5. 가상 상태 `version`이 증가하고 오래된 version으로 변경하면 충돌 처리된다.
6. 세션 reset 후 초기 상태는 복원되지만 감사용 명령 이력은 정책대로 보존된다.
7. 잘못된 JSON 또는 필수 필드 누락은 저장 전에 거부된다.

통과 조건: 정의된 DB 테스트 전부 성공, 운영 DB 파일 변경 없음.

### 15.5 명령 파서와 상태 엔진 테스트

MVP가 지원하는 모든 명령에 대해 정상, 실패, 경계 조건을 각각 작성한다.

| 입력 | 기대 결과 |
|---|---|
| `systemctl stop nginx` | nginx가 `active`에서 `inactive`로 변경 |
| `systemctl stop nginx` 재실행 | 상태 모순 없이 이미 중지된 결과 반환 |
| `systemctl restart nginx` | nginx가 `active`로 변경 |
| `systemctl stop unknown` | 상태 변경 없이 unit 오류 반환 |
| `useradd trainee` | 사용자 추가 후 후속 조회에 반영 |
| 같은 사용자 재생성 | 중복 사용자 오류, 상태 변경 없음 |
| `userdel trainee` | 사용자 삭제 및 관련 상태 정책 적용 |
| `chmod 640 /path` | 파일 mode 변경 |
| 존재하지 않는 파일 `chmod` | 오류 반환, 상태 변경 없음 |
| `ufw deny 22` | SSH 연결 불가 상태로 변경 |
| `ufw allow 22` | SSH 연결 가능 상태로 복구 |
| `apt install nginx` | 패키지 설치 상태 변경 |
| `rm -rf /` | 시뮬레이션 정책에 따른 영향 설명 또는 차단, 실제 실행 없음 |
| `cmd1; cmd2` | MVP 미지원 복합 명령으로 거부 |
| `$(command)`, backtick, pipe | MVP 미지원 셸 확장으로 거부 |

연속 상태 시나리오를 최소 20개 작성하고 처음부터 끝까지 상태 모순이 없는지 확인한다.

통과 조건:

- 고정 상태 전이 테스트 100% 성공
- 미지원 문법이 실제 Docker 또는 호스트에서 실행된 횟수 0회
- 같은 초기 상태와 명령 순서에서 결과가 항상 동일

### 15.6 규칙 기반 채점 테스트

문제 6개마다 다음 fixture를 준비한다.

- 정답 상태
- 부분 성공 상태
- 명령은 맞지만 최종 상태가 틀린 경우
- 우회 명령으로 동일한 목표 상태를 만든 경우
- 힌트 1·2·3단계 사용 후 성공한 경우

채점은 입력한 명령 문자열이 아니라 최종 상태를 우선 평가한다. 정답과 같은 결과를 만든 합리적인 다른 명령도 성공으로 처리한다.

통과 조건: 문제 6개의 성공·실패·부분 성공 fixture를 100% 정확하게 분류.

### 15.7 Bedrock 서비스 mock 테스트

다음 응답을 각각 주입한다.

- 정상적인 스키마 응답
- JSON 앞뒤에 설명이나 코드펜스가 포함된 응답
- 필수 필드 누락
- 너무 긴 문자열
- 허용되지 않은 `hint_level`
- 프롬프트 규칙을 무시하라는 사용자 입력
- 실제 명령 실행을 요구하는 모델 응답
- 빈 응답
- `AccessDeniedException`
- `ValidationException`
- `ThrottlingException`
- 일시적 5xx
- connect timeout과 read timeout

검증 내용:

- 정상 응답만 Pydantic 검증을 통과한다.
- retry 가능한 오류만 제한적으로 재시도한다.
- 권한과 payload 오류는 반복 호출하지 않는다.
- 모든 실패는 `degraded`, `reason`, `retryable`을 포함한 규칙 기반 폴백을 반환한다.
- 모델이 만든 명령은 자동 실행되지 않는다.
- 로그에 JWT, AWS 자격 증명 및 원문 프롬프트 전체가 기록되지 않는다.

통과 조건: 주입한 모든 오류에서 API 500으로 종료되지 않고 정의된 폴백 또는 검증 오류를 반환.

### 15.8 실제 Bedrock 연결 테스트

실제 호출은 관리자가 제공한 role, region, model/profile ID로 backend 컨테이너 안에서 수행한다.

순서:

1. backend 컨테이너가 인식하는 AWS caller ARN 확인
2. 승인 `BEDROCK_REGION`과 `BEDROCK_MODEL_ID` 확인
3. 짧은 한국어 프롬프트로 Converse 호출
4. 5회 연속 호출하여 성공 여부와 지연 시간 기록
5. 입력·출력 토큰과 AWS request ID 기록
6. AI API를 통해 같은 호출을 수행하여 Pydantic 검증과 DB 저장 확인

통과 조건:

- backend 컨테이너에서 5회 연속 호출 성공
- 승인되지 않은 모델을 호출하지 않음
- 응답 또는 로그에 자격 증명 노출 없음
- 한 번의 호출이 설정한 20초 timeout을 넘으면 안전한 폴백 반환
- 실패가 발생하면 오류 코드와 request ID로 원인을 구분할 수 있음

### 15.9 API와 사용자 격리 테스트

- JWT가 없거나 만료되면 401
- 학습 권한이 없는 role이면 403
- 다른 사용자의 session ID 접근은 403 또는 404
- 존재하지 않는 세션은 404
- 잘못된 command payload는 422
- 오래된 상태 version 변경은 409
- 같은 요청을 중복 전송해도 상태가 이중 변경되지 않음
- 세션 소유자만 reset 가능
- AI 채팅과 명령 API에 입력 길이 제한 적용

통과 조건: 인증·인가 및 입력 검증 테스트 100% 성공.

### 15.10 프론트엔드와 단일 터미널 테스트

- 화면에 터미널 UI가 하나만 표시된다.
- 실제·시뮬레이션 모드가 버튼과 색상으로 구분된다.
- 실제 모드 입력은 `/ws/shell`로 전달된다.
- 시뮬레이션 입력은 AI API로만 전달되고 `/ws/shell`로 전달되지 않는다.
- 모드별 화면 버퍼와 명령 이력이 분리된다.
- 시뮬레이션 출력에 항상 `SIMULATION` 표시가 있다.
- 새로고침 후 현재 학습 세션과 문제를 복원한다.
- Bedrock timeout에서 터미널이 멈추지 않고 degraded 안내를 표시한다.
- 모델 출력의 OSC 제어 시퀀스와 위험한 ANSI 시퀀스를 제거한다.
- AI가 제시한 명령은 자동 실행되지 않고 사용자가 직접 입력해야 한다.
- `npm run build`가 성공한다.

통과 조건: 체크리스트 전부 확인하고 주요 화면 캡처 보관.

### 15.11 E2E 학습 시나리오 테스트

다음 순서를 브라우저에서 처음부터 끝까지 수행한다.

1. 로그인 후 학습 세션 생성
2. 진단 문제로 초기 난이도 결정
3. 실제 모드에서 안전한 파일·권한 문제 수행
4. 규칙 기반 채점 결과 확인
5. AI 힌트 1단계와 2단계 요청
6. 시뮬레이션 모드로 전환
7. Nginx 중지 → 상태 확인 → 재시작 → 정상화 수행
8. 방화벽으로 SSH 차단 → 원인 진단 → 복구 수행
9. 완료 점수와 명령·힌트 이력 확인
10. 로그아웃 후 재로그인하여 결과 복원

두 개의 서로 다른 사용자 계정으로 동시에 수행해 상태와 대화가 섞이지 않는지 확인한다.

통과 조건: 문제 6개를 모두 완료하고 DB, 화면과 채점 결과가 일치.

### 15.12 보안 테스트

필수 확인:

- 학생용 `webterm` 컨테이너에서 `169.254.169.254` 접근 불가
- 학생용 컨테이너에서 AWS caller identity 또는 임시 자격 증명 획득 불가
- backend 컨테이너만 승인된 Bedrock 권한 사용 가능
- 시뮬레이션 입력이 subprocess, `os.system`, Docker exec 또는 PTY로 전달되지 않음
- 프롬프트 주입으로 시스템 규칙, 다른 사용자 기록 또는 secret을 얻을 수 없음
- 모델 응답의 HTML, OSC 및 제어문자가 UI 동작을 변경하지 않음
- 다른 사용자의 채팅·명령·가상 상태 접근 불가
- 로그에 JWT, 비밀번호, AWS key와 전체 WebSocket URL이 남지 않음

통과 조건: 위 보안 항목에서 성공적인 우회 0건. 하나라도 실패하면 배포 및 사용자 실험을 중단한다.

### 15.13 성능·안정성·비용 테스트

학교 쿼터와 비용 한도 안에서 다음을 측정한다.

- 실제 Bedrock 호출 최소 30회
- 가능하면 동시 사용자 5명 또는 동시 요청 5개
- API 응답 시간 p50·p95
- Bedrock timeout, throttle과 폴백 비율
- 요청별 입력·출력 토큰
- 문제 1개와 학습 세션 1개당 추정 비용
- 30분 이상 세션에서 DB 및 화면 상태 유지

MVP 목표:

- Bedrock 호출 p95 20초 이하
- 정상 조건의 폴백 비율 5% 미만
- 비 AI API p95 500ms 이하
- 상태 엔진 결과 일관성 100%
- 세션 간 데이터 혼합 0건

학교 쿼터가 낮아 동시 테스트를 허용하지 않으면 관리자와 합의한 최대 부하로 낮추고 논문에 제한사항을 기록한다.

### 15.14 최종 테스트 통과 기준

다음 조건을 모두 만족해야 구현 완료로 판단한다.

- 기존 backend 테스트와 frontend build 통과
- 새 backend AI 테스트 전부 통과
- 문제 6개 E2E 완료
- 상태 전이와 채점 fixture 정확도 100%
- 실제 Bedrock smoke test 성공
- timeout·권한 거부·throttle 폴백 확인
- 학생용 컨테이너의 AWS 자격 증명 접근 차단
- 다른 사용자 데이터 접근 차단
- 시뮬레이션 명령의 실제 실행 0회
- 성능·토큰·비용 측정 결과 기록
- 논문에 사용할 아키텍처, 테스트 조건과 결과 재현 가능

## 16. 논문 평가 계획

제안 시스템의 연구 핵심은 단순한 AI 채팅이 아니라 안전성, 상태 지속성 및 학습 피드백이다.

### 16.1 비교 방식

- 비교군: 대화 기록만 참조하는 순수 LLM 터미널
- 제안 방식: 구조화된 가상 상태와 규칙 기반 채점기를 참조하는 AI 터미널

### 16.2 측정 항목

- 연속 명령 수행 시 상태 모순 발생률
- 전문가 정답 대비 명령 결과 정확도
- 문제 성공·실패 판정 정확도
- 지원하지 않는 명령의 안전한 거부율
- 힌트의 적합성과 단계성
- 문제 완료율과 평균 수행 시간
- Bedrock 응답 지연 시간
- 문제 또는 세션당 호출 비용
- 관리자 승인 모델의 throttle 및 폴백 발생률

학습 참여자를 모집하지 못하면 학습 효과 향상을 주장하지 않고 시스템 구현 및 기능 검증 논문으로 범위를 제한한다. 사람 대상 데이터를 수집할 경우 지도교수와 연구윤리 또는 IRB 필요 여부를 먼저 확인한다.

## 17. 단계별 구현 계획과 통과 조건

각 단계는 구현, 테스트, 통과 조건으로 구성한다. 이전 단계의 통과 조건을 만족하기 전에는 다음 단계의 의존 기능을 완료로 처리하지 않는다.

### 0단계: 현재 프로젝트 기준선 고정 — 0.5일

구현:

- 현재 Git 변경 상태와 실행 환경 기록
- 기존 backend 테스트 결과 저장
- frontend production build 결과 저장
- 실제 Docker 터미널의 정상 동작 화면 캡처

테스트:

- `python test/test_endpoints.py`
- `python test/test_websocket.py`
- `npm run build`
- 로그인, 모니터링, 터미널, 파일 탐색기 수동 확인

통과 조건: 기존 오류와 새로 발생한 오류를 구분할 수 있는 기준선 확보.

### 1단계: 학교 AWS 사용 준비 — 관리자 일정 의존

구현:

- 실행 role ARN, Bedrock 리전과 model/profile ID 설정
- `boto3` 버전 고정
- 임시 smoke test 스크립트 작성
- backend와 webterm의 AWS 자격 증명 접근 경로 분리

테스트:

- backend 컨테이너의 실제 caller ARN 확인
- backend 컨테이너에서 Converse 5회 연속 호출
- webterm 컨테이너의 IMDS 접근 차단 확인
- 오류 코드, request ID, 지연과 토큰 기록 확인

통과 조건:

- backend만 승인 모델 호출 성공
- webterm에서 AWS 자격 증명 획득 불가
- region, model/profile, 쿼터, 비용과 로그 정책 문서화

권한 정책만 적용되고 실제 backend 호출이 실패하면 이 단계는 완료가 아니다.

### 2단계: 시나리오와 테스트 fixture 확정 — 1일

구현:

- 시나리오 3개와 문제 6개 작성
- 문제별 초기 상태, 목표 상태, 성공 조건과 힌트 3단계 정의
- 지원 명령과 미지원 문법 목록 확정
- 20개 이상의 연속 명령 상태 fixture 작성

테스트:

- 각 문제가 Linux 학습 목표와 연결되는지 검토
- 정답, 부분 정답, 오답과 우회 정답 예시 검토
- 실제로 실행하면 위험한 명령이 시뮬레이션 범위에만 있는지 확인

통과 조건: 모든 문제의 입력·상태·정답·채점 기준이 코드 없이도 표로 설명 가능.

### 3단계: DB 모델과 세션 API — 1~2일

구현:

- `ai_learning_sessions`, `ai_virtual_states`, `ai_command_attempts`, `ai_chat_messages` 추가
- 세션 생성, 조회, reset과 history API 구현
- 사용자 소유권과 상태 version 검사

테스트:

- `test_ai_models.py`
- AI API의 401·403·404·409·422 응답
- 두 사용자 데이터 격리
- 재로그인 후 세션 복원

통과 조건: Bedrock 없이 학습 세션과 빈 가상 상태를 생성·복원·초기화할 수 있음.

### 4단계: 명령 파서와 가상 상태 엔진 — 2~3일

구현:

- 허용 명령 파서
- 서비스, 사용자, 파일, 패키지와 방화벽 상태 전이
- 복합 셸 문법과 미지원 명령 거부
- 결정적인 시뮬레이션 출력 데이터 생성

테스트:

- `test_virtual_linux.py`
- 고정 상태 전이와 연속 명령 fixture
- 반복·중복·존재하지 않는 리소스 처리
- 셸 주입 문자열이 실행 경로에 도달하지 않는지 확인

통과 조건: 상태 fixture 100% 통과, 동일 입력의 결과가 항상 동일, 실제 명령 실행 0회.

### 5단계: 커리큘럼과 규칙 기반 채점기 — 1~2일

구현:

- 문제 선택과 난이도 정책
- 상태 기반 성공·부분 성공·실패 판정
- 힌트 단계와 시도 횟수 기록
- 다음 문제 또는 난이도 결정

테스트:

- `test_task_grader.py`
- 문제 6개의 정답·오답·우회 정답 fixture
- 명령 문자열이 달라도 목표 상태가 같으면 성공하는지 확인

통과 조건: 채점 fixture 정확도 100%, Bedrock 없이 전체 문제 진행 가능.

### 6단계: Bedrock 서비스 통합 — 1~2일

구현:

- `services/bedrock.py`
- 학습자 수준, 문제, 상태 요약과 직전 판정으로 프롬프트 구성
- Pydantic 응답 검증
- timeout, 제한된 retry와 규칙 기반 폴백
- 구조화 로그와 토큰·지연 기록

테스트:

- `test_bedrock_service.py` mock 전체 항목
- `test_bedrock_live.py` 실제 모델 호출
- 프롬프트 주입과 잘못된 모델 출력
- 민감정보 로그 검사

통과 조건: mock 오류 전부 안전하게 처리하고 실제 승인 모델 응답을 검증·저장할 수 있음.

### 7단계: AI API 완성 — 1일

구현:

- command, chat, hints와 grade API 연결
- 상태 엔진 결과를 Bedrock 설명 입력으로 전달
- idempotency 또는 상태 version으로 중복 변경 방지
- 입력 길이와 호출 빈도 제한

테스트:

- `test_ai_api.py`
- 인증, 사용자 소유권, 입력 검증과 중복 요청
- Bedrock 정상·degraded 응답 API 계약

통과 조건: API만으로 세션 생성부터 문제 완료와 이력 조회까지 수행 가능.

### 8단계: 단일 터미널 UI와 AI 패널 — 2~3일

구현:

- 실제·시뮬레이션 모드 전환
- 기존 xterm 하나를 두 입력 경로에 연결
- AI 학습 패널, 문제, 힌트와 진행률 표시
- 모드별 버퍼 분리와 세션 복원
- 모델 출력 제어문자 정제와 degraded UI

테스트:

- `npm run build`
- 실제 입력은 WebSocket, 시뮬레이션 입력은 AI API로만 전송되는지 확인
- AI가 만든 명령의 자동 실행이 없는지 확인
- timeout, 재연결, 새로고침과 좁은 화면 확인

통과 조건: 사용자에게 터미널 하나만 보이고 두 모드가 혼동 없이 작동.

### 9단계: 통합·보안·회귀 테스트 — 2일

구현:

- 발견된 결함 수정
- 실험용 계정과 초기 상태 준비
- 테스트 결과와 화면 증거 정리

테스트:

- 기존 테스트 전체 재실행
- 새 AI 테스트 전체 실행
- 사용자 2명의 E2E 시나리오
- IMDS, 명령 주입, 프롬프트 주입, 데이터 격리 테스트
- 문제 6개 처음부터 끝까지 수행

통과 조건: 15.14 최종 테스트 통과 기준을 모두 만족.

### 10단계: 성능 측정과 논문 데이터 수집 — 2~3일

구현:

- 측정 스크립트와 결과 저장 형식 확정
- 테스트 조건, 모델, 리전, 프롬프트 버전 기록
- 아키텍처와 연구 절차 문서화

테스트·측정:

- 실제 호출 최소 30회
- p50·p95, 오류·폴백, 토큰과 비용 측정
- 순수 LLM 방식과 상태 기반 방식의 고정 시나리오 비교
- 전문가 기준으로 출력 정확성과 힌트 적합성 평가

통과 조건:

- 실험을 다시 실행할 수 있는 입력 fixture와 결과 보유
- 논문 표와 그래프를 만들 수 있는 원자료 확보
- 사용자 실험이 없다면 학습 효과가 아닌 시스템 정확성·일관성으로 결론 범위 제한

예상 개발 기간은 관리자 승인 대기 시간을 제외하고 약 13~18일이다. 일정이 부족하면 문제 수를 줄이기보다 지원 명령 종류와 UI 장식을 줄여 핵심 비교 실험을 유지한다.

## 18. 완료 기준

다음 조건을 모두 만족하면 MVP 구현 완료로 판단한다.

- 15.14의 최종 테스트 통과 기준을 모두 만족함
- 사용자에게 터미널 UI가 하나만 표시됨
- 실제 모드에서 기존 Docker 터미널 기능이 유지됨
- 시뮬레이션 명령이 실제 Docker나 호스트에서 실행되지 않음
- 시뮬레이션 모드가 화면에서 명확히 구분됨
- 시나리오 3개와 문제 6개를 수행할 수 있음
- 상태를 변경한 뒤 후속 명령에서 변경 결과가 일관되게 유지됨
- 문제 성공 여부를 규칙 기반으로 판정함
- Bedrock이 학습자 수준에 맞는 설명과 3단계 힌트를 제공함
- 채팅, 명령 시도, 힌트, 수행 결과가 DB에 저장됨
- 로그아웃 또는 새로고침 후 자신의 학습 이력을 복원할 수 있음
- 자동 테스트와 프론트엔드 빌드가 통과함
- 학교가 승인한 실행 역할과 model/profile로 smoke test가 통과함
- 학생용 `webterm` 컨테이너에서 EC2 임시 자격 증명에 접근할 수 없음
- 권한 거부와 timeout에서 규칙 기반 폴백이 표시됨
- 리전, 모델, 쿼터, 비용 및 로그 정책이 문서화됨

## 19. MVP 제외 범위

- 실제 Linux 전체 명령 지원
- LLM이 임의 명령을 직접 실행하는 자율 에이전트
- 실제 Docker 상태와 가상 서버 상태의 자동 동기화
- 복잡한 Bash 스크립트와 모든 파이프 처리
- 실제 서버에서 `sudo`, 디스크 초기화 또는 방화벽 변경 실행
- 사용자가 만든 임의 시나리오 자동 실행
- 모델 파인튜닝

이 항목들은 논문 제출 이후의 확장 과제로 둔다.
