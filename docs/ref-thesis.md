# 논문 작성용 참조 파일 정리

* 대상 논문: `실시간 시스템 모니터링 데이터를 활용한 생성형 AI 기반 Linux 운영 학습 지원 시스템`
* 목차 원본: `docs/1/논문-목차(흐름).txt`
* 정리 기준일: 2026-08-05
* **논문 범위: 시스템 설계·구현 논문.** AI 비교 실험(`pure_llm` 대 `structured_state`)은 사용하지 않는다. 근거와 대체 자료는 §5.

---

## 0. 현재 구현 상태

AI 학습 지원 기능은 **구현 완료**다. Bedrock 연동, 가상 Linux 상태 엔진, 규칙 기반 채점기, 프론트 화면이 모두 코드로 존재한다.

| 구성 요소 | 파일 | 줄 수 |
|---|---|---:|
| AI 학습 API | `backend/routers/ai_tutor.py` | 448 |
| Bedrock 클라이언트 | `backend/services/bedrock.py` | 373 |
| 커리큘럼 탐색·힌트·진도 | `backend/services/curriculum.py` | 248 |
| 가상 Linux 상태 엔진 | `backend/services/virtual_linux.py` | 188 |
| **규칙 기반 채점기** | `backend/services/task_grader.py` | 158 |
| 스키마 | `backend/schemas/ai_tutor.py` | 149 |
| 명령 파서 | `backend/services/command_parser.py` | 75 |
| 호출량 제한 | `backend/services/ai_rate_limit.py` | 37 |
| DB 마이그레이션 | `backend/migrations/versions/0002_ai_tutor_tables.py` | 177 |
| 벤치마크 | `backend/benchmarks/stage10.py` | 273 |
| 시나리오 fixture | `backend/test/fixtures/ai_learning_scenarios.json` | — |
| 프론트 화면 | `frontend/src/pages/AITutor.jsx` | 266 |

규모: 백엔드 10,910줄, 프론트엔드 7,430줄, 테스트 파일 30개.

DB 테이블은 8개다. 모니터링 3개(`monitor_snapshots`, `web_users`, `login_logs`)와 AI 5개(`ai_learning_sessions`, `ai_virtual_states`, `ai_command_attempts`, `ai_chat_messages`, `ai_interaction_audits`).

---

## 1. 1장 서론 / 2장 관련 연구 및 기술 배경

| 파일 | 용도 |
|---|---|
| `docs/1/논문-목차(흐름).txt` | 목차 원본. 상단에 논문 10편의 구성 패턴이 정리되어 있어 장 구성 결정에 참고 |
| `docs/evaluation.md` §1~2 | 연구 배경과 필요성. 최초 평가에서 확인된 문제와 위험 |
| `docs/aws_ref.md` §1 먼저 기억할 결론 | 2.4 Amazon Bedrock 기술 배경 |
| `docs/aws_ref.md` §2 Polylog에서 실제로 사용한 구조 | 선행 프로젝트의 실사용 아키텍처 |

---

## 2. 3장 시스템 설계

### 2.1 전체 구조 (3.1)

| 파일 | 용도 |
|---|---|
| `README.md` | 아키텍처 다이어그램, 기술 스택 표, API 엔드포인트 표, 권한 행렬 |
| `docs/operations.md` | 실제 배포·실행 절차, 환경변수 정의 |
| `docker-compose.yml`, `Dockerfile.webterm` | 서비스 구성과 셸 샌드박스 격리 설계 |
| `frontend/nginx.conf` | 리버스 프록시, TLS 종료, 보안 헤더, rate limit |
| `docs/contracts/security-contract.md` | **권한·인증 계약의 단일 기준.** 3.3 설계와 4장 검증의 근거 |
| `docs/1/AWS 기반 시각화 GUI 교육 시스템 v2.pptx` | 시스템 구성도. Figure 원본 |

### 2.2 데이터 수집 및 처리 구조 (3.2)

| 파일 | 용도 |
|---|---|
| `backend/core/models.py` (286줄) | ERD 근거. 모니터링 3개 + AI 5개 테이블 |
| `docs/1/KAICTS_ERD.pptx` | ERD 도식 |
| `docs/db-operations.md` | Alembic 스키마 버전 관리, fail-closed 마이그레이션 설계 |
| `backend/services/scheduler.py` | 주기적 스냅샷 수집 |

### 2.3 Bedrock 연동 설계 (3.4)

| 파일 | 용도 |
|---|---|
| `backend/services/bedrock.py` (373줄) | 실제 호출 경로, 오류 분류, 폴백 |
| `backend/services/ai_rate_limit.py` | 호출량 제한 설계 |
| `docs/aws_ref.md` §3 트러블 이슈와 교훈 (3.1~3.10) | **설계 결정의 실증적 근거.** 리전 불일치, inference profile 필요성, temperature 분리, JSON 강제 실패 |
| `docs/aws_ref.md` §4 새 프로젝트 권장 구성 | 환경변수, IAM, 재시도, 관측성 |
| `docs/aws_ref.md` §6 오류별 빠른 진단표 | 오류 처리 설계 |

리전 `us-east-1`, inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0`, API는 Converse로 고정되어 있다.

### 2.4 가상 상태 엔진과 학습 시나리오 (3.5)

| 파일 | 용도 |
|---|---|
| `backend/services/virtual_linux.py` (188줄) | **제안 방식의 핵심 기여.** 가상 Linux 상태 전이. `execute_command()`가 미지원 문법이면 상태를 바꾸지 않고 `unsupported_syntax` 반환 |
| `backend/services/command_parser.py` (75줄) | 명령 파싱. 지원 문법 판정의 실제 지점 |
| `backend/services/task_grader.py` (158줄) | **규칙 기반 채점기.** `grade_problem()`이 상태 복사본에 success → partial → failure 순으로 규칙을 대조 |
| `backend/services/curriculum.py` (248줄) | 채점이 아니라 문제 선택·힌트·진도 관리 (`select_problem`, `next_problem`, `hint_for_problem`, `progress_after_grade`) |
| `docs/ai-learning-scenarios.md` | 시나리오·채점 의미의 사람이 읽는 설명 |
| `backend/test/fixtures/ai_learning_scenarios.json` | 위 문서의 기계 판독 원본 |

채점은 명령 문자열 일치가 아니라 **최종 가상 상태가 목표 상태를 충족하는지**로 판정한다. 이 설계가 순수 LLM 대비 차별점이며, 코드에서도 fixture의 `execution_policy.grading_principle`이 `final_state_first`이고 `task_grader.py`의 docstring이 "Deterministic, state-first grading"으로 일치한다.

---

## 3. 4장 시스템 구현

### 3.1 백엔드 (4.1)

| 파일 | 줄 수 | 용도 |
|---|---:|---|
| `backend/routers/shell.py` | 484 | 웹터미널 Docker PTY |
| `backend/routers/ai_tutor.py` | 448 | AI 학습 세션·질의응답 API |
| `backend/routers/admin.py` | 282 | 사용자 관리, 감사 로그 |
| `backend/routers/websocket.py` | 262 | 실시간 모니터링 스트리밍 |
| `backend/routers/auth.py` | 257 | 인증, ticket 발급 |
| `backend/core/security.py` | 222 | JWT, WebSocket ticket |
| `backend/main.py` | 215 | 앱 구성, 마이그레이션 startup |

### 3.2 프론트엔드 (4.2)

| 파일 | 줄 수 | 용도 |
|---|---:|---|
| `frontend/src/pages/Network.jsx` | 492 | 네트워크 모니터링 |
| `frontend/src/api/client.js` | 350 | 통신 계층 |
| `frontend/src/pages/Filesystem.jsx` | 307 | 파일 탐색기 |
| `frontend/src/pages/AITutor.jsx` | 266 | **AI 학습 화면** |
| `frontend/src/components/CPUChart.jsx` | 232 | Recharts 시각화 |
| `frontend/src/features/filesystem/filesystemModel.js` | 238 | 상태 모델 분리 |

### 3.3 실시간 모니터링 (4.3)

`backend/routers/websocket.py`, `backend/services/metrics_collector`(공유 수집기), `frontend/src/components/WebSocketStatus.jsx`.

### 3.4 AI 질의응답 및 설명 생성 (4.4)

`backend/routers/ai_tutor.py` + `services/bedrock.py` + `services/virtual_linux.py` + `services/curriculum.py`의 조합. 관련 테스트는 아래 5절.

---

## 4. 5장 적용 및 기대 효과

| 파일 | 용도 |
|---|---|
| `docs/ai-learning-scenarios.md` | 5.1 학습 시나리오 |
| `docs/re-evaluation.md` | **5.2~5.3의 정량 근거.** 아래 4.1 참조 |
| `docs/evaluation.md` | 위 비교의 "최초" 값. 두 문서는 같은 항목·같은 배점 |
| `docs/tutorials/README.md` | 7단계 학습 과제. 교육 활용 사례 |
| `docs/re-progress.md` Known Limitations | 5.4 한계점 |

### 4.1 평가 점수 (`docs/re-evaluation.md`)

같은 항목·같은 배점으로 재평가한 결과다. 기준일 2026-08-03.

| 관점 | 최초 | 재평가 | 목표 |
|---|---:|---:|---:|
| 시니어 개발자 | 46 | **78** | 75 |
| 학습자 | 63 | **84** | 80 |

항목별로는 보안 4→17, 안전한 실습과 확장 10→21의 개선 폭이 가장 크다.

---

## 5. 논문 범위 결정: AI 비교 실험 제외

**결정(2026-08-05, 사용자):** `pure_llm` 대 `structured_state` 비교 실험을 논문에서 **사용하지 않는다.** 이 논문은 시스템 설계·구현 논문으로 범위를 정한다.

### 5.1 결정 근거

`docs/benchmarks/stage10/`의 live 실행(`stage10-bd7accc484d8`)은 유효 표본을 얻지 못했다. 40회 호출 중 전송은 40/40 성공했으나 모든 응답이 strict JSON 파싱·스키마 검증을 통과하지 못해 `successes: 0`, `target_successes_reached: false`다. 따라서 두 방식의 품질을 비교할 근거가 없다.

### 5.2 쓰지 않을 것

다음은 **논문에 인용하지 않는다.** 데이터 파일은 이력 보존을 위해 저장소에 남겨 두지만 논문의 근거로 삼지 않는다.

* 두 방식의 품질 비교 일체 (정확도, 판정 일치율, 오류율)
* `contradiction_rate: 0.0` — **유효 표본 0건에서 나온 값이다.** "모순이 없었다"가 아니라 "측정하지 못했다"는 뜻이므로 성과로 읽으면 안 된다
* `grade_agreement_rate`, `parse_success_rate`
* 호출 비용 — `estimated_cost: null`
* 힌트 적합성 — `human_expert_hint_suitability: "not_evaluated"`

### 5.3 대신 근거로 쓸 것

비교 실험 없이도 실제로 실행해 확인한 값들이다. 5장과 6장은 이 자료로 구성한다.

| 근거 | 수치 | 출처 |
|---|---|---|
| 코드 품질·보안 개선 | 시니어 46 → **78**, 학습자 63 → **84** | `docs/re-evaluation.md` |
| 권한 행렬 전수 검증 | 21개 경로 × 4개 역할, **86 PASS** | `backend/tests/test_authorization_matrix_e2e.py` |
| 동시 접속 실측 | 모니터링 WebSocket **50/50** 연결, 첫 데이터까지 5.2초 | `docs/re-progress.md` Validation Log |
| 상태 규칙 엔진 결정성 | 표본 300개, **결정성 1.0**, p50 0.065 ms | `stage10` 요약의 `state_rule_benchmark` |
| 로그 비밀 비노출 | 실제 발급 토큰·ticket 원문 대조, **노출 0건** | `docs/re-progress.md` RELEASE-01 #2 |
| 셸 격리 | 심볼릭 링크 탈출 차단 7건 통과 | `backend/tests/test_shell_file_tree.py` |

`state_rule_benchmark`는 Bedrock을 거치지 않고 규칙 엔진만 300회 실행한 결과라 위 파싱 실패와 무관하다. "같은 입력에 항상 같은 상태를 만든다"는 설계 주장의 근거로 쓸 수 있다.

### 5.4 논문에서 쓰는 표현

- 쓸 수 있음: "가상 상태와 규칙 기반 채점을 분리해 **설계·구현했다**", "규칙 엔진의 결정성을 300회 실행으로 확인했다"
- 쓸 수 없음: "제안 방식이 순수 LLM보다 **정확하다/우수하다**", "모순율이 0이었다"

5장은 목차대로 `적용 및 기대 효과`로 쓰고, 비교 우위 주장 대신 학습 시나리오와 설계상의 차이를 서술한다. 실험 재실행은 6장 향후 연구로 미룬다.

---

## 6. 검증 및 실험 재현

| 파일 | 용도 |
|---|---|
| `docs/stage10-benchmark-method.md` | 벤치마크 재현 절차. **비교 실험은 논문에서 제외**(§5)했으므로 6장 향후 연구의 재실행 절차로만 참조 |
| `backend/test/test_bedrock_service.py` (237줄) | Bedrock 클라이언트 검증 |
| `backend/test/test_bedrock_live.py` | 실호출 검증 |
| `backend/test/test_ai_api.py` (321줄) | AI API 검증 |
| `backend/test/test_ai_security.py` (201줄) | AI 경계 보안 검증 |
| `backend/test/test_task_grader.py` | 채점기 검증 |
| `backend/tests/test_authorization_matrix_e2e.py` (299줄) | 권한 행렬 21개 경로 E2E, 86 PASS |
| `backend/tests/test_secret_logging.py` (207줄) | 로그 비밀 비노출 |
| `backend/tests/test_metric_reliability.py` (218줄) | 메트릭 신뢰성 |
| `frontend/src/test/accessibility.test.jsx` (249줄) | 접근성 |
| `scripts/gate.sh` | 전체 검증 1회 실행기 |
| `docs/re-progress.md` Validation Log | 실제 구동 검증 기록. 50/50 동시 WebSocket 연결 5.2초 등 실측치 포함 |

---

## 7. 문서-코드 대조 결과

논문에 인용하기 전에 문서의 주장을 실제 코드로 확인한 기록이다. 문서에만 있고 구현과 다른 항목이 없는지 대조했다.

| 문서의 주장 | 출처 | 코드 확인 | 판정 |
|---|---|---|---|
| 리전 `us-east-1` | `stage10-benchmark-method.md` | `bedrock.py:28` `REGION = "us-east-1"` | 일치 |
| inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 같음 | `bedrock.py:29` `MODEL_ID` | 일치 |
| API는 Converse | 같음 | `bedrock.py:208` `self._client.converse(` | 일치 |
| 시나리오 3개 / 문제 6개 / step 24개 | `ai-learning-scenarios.md` | fixture 파싱 결과 3 / 6 / 24 | 일치 |
| 힌트 3단계 | 같음 | fixture `hints` 길이 3, `task_grader.py`가 `hint_level` 0~3 강제 | 일치 |
| 최종 상태 우선 채점 | 같음 | fixture `execution_policy.grading_principle = "final_state_first"` | 일치 |
| 미지원 문법은 상태 변경 없음 | 같음 | `virtual_linux.py:55` 미지원 시 `before` 상태를 그대로 반환 | 일치 |
| 채점기가 `curriculum.py`에 있음 | (이 문서의 초기 오기) | 실제로는 `task_grader.py`. `curriculum.py`는 탐색·힌트·진도 | **수정함** |
| 거부 문법 6종 | `ai-learning-scenarios.md` 표 | fixture는 8종. 표에 없는 리다이렉션(`>`, `>>`, `<`, `2>`)과 임의 셸 스크립트가 더 있음 | **문서가 축약** |
| AI 테이블 4개 | 과거 계획 문서 | 실제 5개 (`ai_interaction_audits` 추가) | **구현이 더 많음** |

`docs/ai-learning-scenarios.md`의 거부 문법 표는 fixture의 부분집합이다. 논문에 거부 문법을 나열할 때는 문서가 아니라 fixture(`rejected_shell_syntax`)를 근거로 삼아야 한다.

## 8. 작성 시 주의할 점

1. **AI 비교 실험은 논문에서 제외했다(§5).** `docs/benchmarks/stage10/`의 수치를 성과로 인용하지 않는다. 특히 `contradiction_rate: 0.0`은 유효 표본 0건에서 나온 값이라 "모순 없음"이 아니라 "측정 불가"다.

2. **README와 실제 배포 환경이 다르다.** 배포 EC2는 도메인 발급이 불가해 고정 IP만 쓰며, 운영 HTTPS 프로필이 아니라 개발 override가 실제 배포 모드다. 절차의 정본은 `docs/operations.md`다.

3. **RELEASE-01은 `PASS`이지 `DONE`이 아니다.** 브라우저 기반 수동 검사 3건을 `DEC-BROWSER-SKIP`으로 생략했다. 근거는 `docs/re-progress.md`.

4. **남은 위험 7건**이 `docs/re-evaluation.md`에 우선순위와 함께 있다 — 로그아웃 토큰 무효화 부재, 단일 프로세스 가정, 관측 가능성 부재, CI 미실행, Windows 셸 부재, 대상 하드웨어 미측정, Git 이력 blob. 6장 한계점과 향후 연구에 그대로 쓸 수 있다.

5. **비용 수치는 없다.** `estimated_cost`가 `null`이라 금액은 논문에 적을 수 없다. 비용을 언급해야 하면 5.3의 토큰 수까지만 쓴다.

6. **5장을 "실증 분석"으로 쓰지 않는다.** 목차대로 `적용 및 기대 효과`다. 사람 대상 학습 효과 실험을 하지 않았으므로 학습 효과 향상을 주장하지 않는다.
