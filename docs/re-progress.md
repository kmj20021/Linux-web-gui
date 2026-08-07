# Re-plan Progress

## Decisions

| ID | 결정값 | 근거 | 상태 |
| --- | --- | --- | --- |
| DEC-01 | 사용자 ID 컬럼은 `username`을 유지한다. | 현재 ORM과 DB 및 `docs/re-plan.md` 권장 기본값 | CONFIRMED |
| DEC-02 | 전역 관리자 모델을 사용하고 `created_by`는 감사 정보로만 사용한다. | 관리자 권한 예측 가능성 및 계획 권장 기본값 | CONFIRMED |
| DEC-03 | admin만 교육용 `demo-*` 자식 프로세스를 종료할 수 있다. | 최소 권한 및 계획 권장 기본값 | CONFIRMED |
| DEC-04 | 60초 이하의 일회성 WebSocket ticket을 사용한다. | access token 노출 축소 및 계획 권장 기본값 | CONFIRMED |
| DEC-05 | 운영 프로필은 인증서가 없으면 시작에 실패하고 HTTP는 개발 프로필에서만 허용한다. | TLS 우회 방지 및 계획 권장 기본값 | CONFIRMED |
| DEC-06 | 셸 컨테이너 네트워크는 기본 `none`이며 별도 개발 설정에서만 제한적으로 허용한다. | 호스트·네트워크 경계 축소 및 계획 권장 기본값 | CONFIRMED |
| DEC-07 | CPU·메모리·디스크·히스토리는 로그인 사용자에게, 연결 목록은 admin에게 허용한다. | 민감도별 최소 권한 및 계획 권장 기본값 | CONFIRMED |
| DEC-08 | 원본 스냅샷은 7일 후 삭제한다. | 데이터 보존 정책 및 계획 권장 기본값 | CONFIRMED |
| EXC-01 | 사용자 승인 순서 예외: QA-03 차단 해소에 한해 `SECRET-01 → SECRET-02 → QA-03`을 Phase 1 Gate 전 선행한다. | PLAN-SIMPLIFY-01이 이 순서를 공식 Phase 1 Wave로 반영했다. 이력 보존용이며 더 이상 활성 예외가 아니다. | SUPERSEDED |
| PLAN-SIMPLIFY-01 | 사용자 승인 계획 조정: 위험도별 검증, Wave/Phase Gate 회귀, npm/DB/runtime 정책, PM-owned CI와 Back-owned scanner를 적용한다. | 안전 검증을 유지하면서 중복 실행과 CI inline scanner 복잡도를 줄이는 명시적 승인 | APPROVED |
| DEC-RUNTIME-DEFER | 사용자 승인: PLAN-SIMPLIFY-02가 Phase 3·4 게이트에 추가한 **실제 구동 검증**은 두 Phase 게이트를 이미 통과한 뒤 도입됐으므로 소급 실행하지 않고, `docs/re-plan.md` §14 `RELEASE-01`의 수동 검사(항목 1·2·3·5·6·10)에서 1회로 통합 실행한다. | Phase 3·4 게이트 통과 시점에는 해당 요구가 존재하지 않았고, `RELEASE-01`이 동일 검증 항목(권한 행렬, 로그 JWT/ticket 비노출, 셸 네트워크·Docker 차단, 심볼릭 링크 탈출, 운영 HTTP·8000 차단)을 이미 포함한다. Phase 7 이전에 중복 실행할 실익이 없다. | APPROVED |
| DEC-BROWSER-SKIP | 사용자 결정: `RELEASE-01` 수동 검사 중 **실제 브라우저가 필요한 항목을 실행하지 않는다.** 대상은 9(키보드 기반 주요 화면 사용), 2의 브라우저 콘솔·네트워크 탭 확인, 그리고 화면에서의 터미널 WebSocket 연결 확인이다. | 사용자가 "마우스를 못 쓰는 사람을 배려할 정도의 세심함을 요하는 프로젝트가 아니다"라고 판단했다. 접근성 구현(FRONT-03)과 자동 검사 12건은 이미 통과한 상태로 유지하며, 이번 결정은 **수동 재확인만** 생략한다. 터미널 UI 확인은 backend 가 Windows 에서 셸 라우터를 등록하지 못하는 환경 문제로 로컬에서 재현 불가였고, 서버 측 격리·권한은 18/18 및 권한 행렬로 이미 검증됐다. | APPROVED |
| PLAN-SIMPLIFY-02 | 사용자 승인 계획 조정: codex 멀티에이전트용 조율 장치(파일 소유권 잠금 테이블, Wave 병렬 규칙, 작업별 독립 Test Agent 재검증, YAML 작업 패킷, 통합 담당자 병합)를 제거하고 `docs/re-plan.md` §3 단일 에이전트 순차 실행으로 대체한다. §3.2 표준 완료 게이트를 도입하고, 보안 Phase 3(인증·배포)·4(셸 격리) 게이트에 실제 구동 검증 1회(docker compose up → 권한 행렬 curl → 로그 JWT grep; 실제 셸 컨테이너 네트워크·소켓 차단)를 추가한다. 로드맵·보안 내용과 Phase 0~4 본문은 보존한다. | 클로드 코드 단일 에이전트로 전환하면서 조율 장치가 순수 오버헤드가 됐다. Validation Log의 반복된 TIMEOUT_NO_RESULT·RUNTIME_FAILURE_NO_CHANGE·agent thread limit(ADMIN-01 재시도 6회)이 그 비용을 보여준다. 또한 검증이 전부 mock/정적이라 Known Limitations에 실제 Docker·브라우저·DB 미실행이 반복돼 실제 동작을 보장하지 못했으므로 보안 게이트에 실제 구동을 추가했다. | APPROVED |
| AI-NARRATE-SCOPE | 사용자 결정(대화): AI 튜터의 미지원/무관 명령 처리에 실시간 Bedrock 나레이션을 추가하되, 쉘 인젝션 패턴(`;`, `&&`, `\|`, backtick, 리다이렉션 등)을 포함한 **모든** `unsupported_syntax` 명령에 대해 Bedrock을 호출한다(스킵하지 않음). 대신 인젝션 패턴으로 분류된 명령에는 별도 프롬프트 지시("그럴듯한 실행 결과를 지어내지 말고 거부 이유만 설명하라")를 준다. | 사용자가 "전부 포함"을 원했다. 스킵하면 비용은 아끼지만 원래 목표("AI를 그냥 붙인 게 아니라 실제로 반응하게")를 약화시킨다. 위험은 인젝션 패턴 명령이 "시뮬레이션상 성공한 것처럼" 보이는 교육적 오해였고, 이는 상태/채점을 건드리지 않는 것과 별개 문제라 프롬프트 지시 분기로 해소했다. | APPROVED |
| AI-NARRATE-TOOLCONFIG | 이번 narrate 경로만 Bedrock Converse `toolConfig`(강제 tool-use 구조화 출력)를 도입한다. 기존 `chat`/`hint`가 쓰는 `tutor()`/`build_prompt()`(프롬프트 텍스트로 JSON 요청 + 코드펜스 정규식 파싱)는 이번 범위에서 바꾸지 않는다. | `docs/ref-thesis.md` §5의 stage10 벤치마크가 기존 방식(프롬프트 텍스트 JSON 요청)의 실패 유형(40/40 스키마 검증 실패: 코드펜스·설명 혼입·잘린 응답)을 이미 실증했다. `toolConfig`는 `aws_ref.md:214`가 권장한 정공법이며 IAM 권한 추가 없이(`bedrock:InvokeModel`에 이미 포함) 쓸 수 있다. `tutor()`를 함께 바꾸면 이미 검증된 채점 지원 경로(`chat`/`hint`)를 건드리게 되므로 범위를 narrate 전용으로 좁혔다. | APPROVED |

## Task Status

| Task | Phase/Wave | 상태 | 담당 | 선행 작업 | 검증 |
| --- | --- | --- | --- | --- | --- |
| BASE-01 | Phase 0 / SERIAL | DONE | PM | 없음 | Main Gate 공백 오류 1건 수정 후 기존 Test Agent 재검증 PASS 및 Gate 재통과 |
| BASE-01 Front | Phase 0 / SERIAL | NOT_APPLICABLE | Front | 없음 | 읽기 전용 검토 완료: 문서화 단계로 프론트 변경 없음 |
| BASE-01 Back | Phase 0 / SERIAL | NOT_APPLICABLE | Back | 없음 | 읽기 전용 검토 완료: 문서화 단계로 백엔드·DB 변경 없음 |
| BASE-02 | Phase 0 / SERIAL | DONE | PM | BASE-01 | Main Gate 공백 오류 2건 수정 후 기존 Test Agent 재검증 PASS 및 Gate 재통과 |
| QA-01 | Phase 1 / Wave 1A | DONE | Back | Phase 0 Gate | 자체·독립 pytest 검증 및 Wave 1A 통합 회귀 통과; 추적 DB 불변 |
| QA-02 | Phase 1 / Wave 1A | DONE | Front | Phase 0 Gate | 초기 BLOCKED 후 승인된 5파일 최소 수정, 자체·독립 검증 및 Wave 1A 통합 회귀 통과 |
| SECRET-01 | Phase 1 / Wave 1B | DONE | Back | QA-01, QA-02 | focused/full pytest·독립 Test PASS·통합 회귀·추적 DB 불변 확인; PLAN-SIMPLIFY-01이 예외 순서를 정식 Wave로 승격 |
| SECRET-02 | Phase 1 / Wave 1C | DONE | Back + Front | SECRET-01 DONE | Back·Front 독립 Test PASS, backend/frontend 회귀 및 DB 불변 확인; PLAN-SIMPLIFY-01이 정식 Wave로 승격 |
| PLAN-SIMPLIFY-01 | Plan adjustment / SERIAL | DONE | PM | 사용자 승인 | L0~L3, Wave/Phase Gate, npm·환경·DB·runtime·공백·PM CI 소유 정책과 정식 Phase 순서를 반영; Front는 L0 NOT_APPLICABLE (문서·workflow process 범위만) |
| PLAN-SIMPLIFY-02 | Plan adjustment / SERIAL | DONE | Main | 사용자 승인 | `docs/re-plan.md` §1 원칙 축소·§3 조율 절 전면 교체(단일 순차 실행 + §3.2 표준 게이트)·Phase 2~8 게이트 통일·Phase 3·4 실제 구동 검증 추가·§16 체크리스트 정리를 개정. 후행 공백 0건, 잠금/Wave/통합담당자 잔재 제거 확인. Phase 0~4 본문은 역사 기록으로 보존 |
| QA-03-SCAN | Phase 1 / Wave 1D | DONE | Back | PLAN-SIMPLIFY-01 | focused pytest/current scan 및 독립 Test Agent six-category·redaction·scope 검증 PASS; Phase 1 Gate 통합 완료 |
| QA-03 | Phase 1 / Wave 1D | DONE | PM (workflow) + Back (scanner) | SECRET-02, PLAN-SIMPLIFY-01, QA-03-SCAN PASS | CI가 유지보수 가능한 `python scripts/security_scan.py`를 마지막 단계에서 fail-fast 실행하며 독립 Test·Phase 1 Gate PASS |
| AUTHZ-01 | Phase 2 / Wave 2A | DONE | Main (user-approved exception) + Test | Phase 1 Gate DONE, DEC-03 | 서버 admin·app-managed live `demo-*` 및 서버 PPID 경계, viewer UI 숨김, 독립 권한 행렬 및 Phase 2 Gate 통과 |
| AUTHZ-02 | Phase 3 / Wave 3A | DONE | Back + Test + PM | Phase 2 Gate DONE, BASE-02, DEC-07 | focused·독립 권한 행렬과 Wave 3A backend 회귀 통과 후 DONE으로 승격했다. |
| ADMIN-01 | Phase 3 / Wave 3A | DONE | Back + Test + PM | Phase 2 Gate DONE, DEC-02 | DEC-02 전역 범위와 단일 프로세스 `asyncio.Lock` 마지막 활성 admin 보호를 구현했다. focused·독립 검증 및 Wave 3A backend 회귀 통과 후 잠금을 해제했다. |
| WS-01 | Phase 3 / Wave 3B | DONE | Back + Front + Test + PM | AUTHZ-02 DONE, SECRET-02 DONE, DEC-04 CONFIRMED | 목적별 one-use ticket, 첫 메시지 인증, DB 활성·역할 재검증과 URL credential 제거를 구현했다. focused·독립 검증 및 Wave 3B 회귀 통과 후 잠금을 해제했다. |
| DEPLOY-01 | Phase 3 / Wave 3C | DONE | Back + Test + PM | WS-01 DONE, DEC-05 CONFIRMED | production fail-closed, backend 비공개 및 explicit development HTTP 분리를 구현·독립 검증·Gate로 확인했다. |
| SHELL-01 | Phase 4 / SERIAL | DONE | Back + PM + Test | Phase 3 Gate PASS | viewer 우회 재현을 `get_current_admin` DB-current 역할 강제와 route 음성 검사로 보정했다. focused 7 PASS·compileall PASS·독립 재검증 PASS 뒤 Wave backend 회귀 `python -m pytest backend/tests` 59 PASS를 1회 완료했다. |
| SHELL-02 | Phase 4 / SERIAL | DONE | PM + Back + Front + Test | SHELL-01 DONE, DEC-06 CONFIRMED | network none·read-only/cap-drop/NNP/tmpfs/non-root, session/cleanup limits, proxy-only Docker socket 및 lazy FileExplorer를 구현했다. focused·독립 검증과 Phase 4 Gate를 통과했고 잠금을 해제했다. |
| DB-01 | Phase 5 / SERIAL | DONE | Main | Phase 4 Gate DONE, DEC-01 CONFIRMED | Alembic 스키마 버전 관리 도입: startup 자동 마이그레이션(`alembic upgrade head`, fail-closed)이 ad-hoc `ALTER TABLE`(`ensure_web_users_columns`)을 대체, 현재 모델과 반대인 `rename_username_to_login_id.py`를 명시적 no-op화, 멱등 초기 리비전 `0001`(created_by 포함). focused backend 70 passed·compileall·security scan 0·compose config·공백 검사 통과. 실제 DB 미접근. REPO-01 완료 후 Phase 5 Gate 1회 통과로 DONE 승격. |
| REPO-01 | Phase 5 / SERIAL | DONE | Main (사용자 승인) | DB-01 DONE | 사용자 승인 하에 추적 venv(4,717)·pyc/pycache(8)·실행 DB 2건을 `git rm --cached`로 추적 제거(로컬 파일·해시 보존, 스크래치패드 백업 동일 해시 확인). `.gitignore`에 `*.db` 등 추가. 소스 기능 변경 0의 단독 커밋 `5356a3b`. 사용자 기존 스테이징 11건은 커밋 제외 후 원상 복원. `git ls-files` venv/pyc/db 0건, 총 4831→104. |
| PERF-01 | Phase 6 / SERIAL | DONE | Main | Phase 5 Gate DONE | 단일 백그라운드 `MetricsCollector`(`services/metrics_collector.py`)가 5초마다 immutable snapshot 1개를 만들고, WebSocket 연결과 스케줄러가 이를 공유(fan-out)한다. `collect_metrics` 블로킹 psutil을 `asyncio.to_thread`로 offload, 수집기 lifecycle을 startup/shutdown에 명시. focused 8 PASS·Phase 6 Gate 통과. |
| PERF-02 | Phase 6 / SERIAL | DONE | Main | PERF-01, SHELL-02 DONE | 셸 컨테이너 start/cleanup 블로킹(docker rm·Popen·proc wait)을 `start_async`/`cleanup_async`(`asyncio.to_thread`)로 offload, `_cleaned` 가드를 `threading.Lock`으로 스레드 안전화해 취소·동시 호출에도 정리를 정확히 1회 실행. focused 5 PASS·Gate 통과. |
| DOC-01 | Phase 8 / SERIAL | DONE | Main | Phase 7 Gate DONE | `README.md` 전면 개정(디렉터리 구조, 권한 행렬, ticket 인증과 5초 주기, 관리자 CLI, TLS 조건, 셸 격리 제한, 검증 명령, psutil OS 차이·문제 해결), 신규 `docs/operations.md`(환경변수, 로컬 개발, 개발/운영 프로필, 인증서 발급, 배포 후 확인, 운영 제한사항). 과거 보고서 2건에 "현재 동작 아님" 표를 붙여 무엇이 달라졌는지 명시. README 경로와 OpenAPI를 기계 대조해 양방향 차이 0건 확인. Phase 8 Gate 1회 통과로 DONE 승격. |
| STUDY-01 | Phase 8 / SERIAL | DONE | Main (사용자 승인 축소 범위) | DOC-01 | `docs/tutorials/README.md` 신규. 계획의 7단계 순서와 6개 필수 요소(목표·관련 파일·위험 사항·실패 테스트·완료 테스트·복습 질문)를 모두 담되, **답과 테스트 코드는 쓰지 않는다.** 사용자가 "완성된 코드를 필요할 때 뜯어보는" 방식으로 학습하기로 해(대화 결정), 커리큘럼 대신 자가진단용 질문과 포인터로 축소했다. 실패 테스트는 코드가 아니라 명세로 제시해 구현은 학습자가 하도록 남겼다. 인용한 파일 경로·테스트 경로·수치(세션 한도 1/5, backend `expose` 무바인딩)를 실제 코드와 대조해 검증했다. 인용 테스트 9개 경로 141건 수집 확인. |
| RELEASE-02 | Phase 9 / SERIAL | DONE | Main | RELEASE-01 PASS | `docs/re-evaluation.md` 신규. `docs/evaluation.md`와 동일 항목·동일 배점으로 재평가했다. 시니어 **46 → 78**(목표 75), 학습자 **63 → 84**(목표 80). 각 점수의 근거를 실행한 검증으로만 제시하고 감점 사유를 함께 적었다. §14 릴리스 조건 5개 중 4개 충족, "실행하지 못한 필수 검사 0건"만 `DEC-BROWSER-SKIP`으로 미충족이다. 남은 위험 7건(로그아웃 토큰 무효화 부재, 단일 프로세스 가정, 관측 가능성 부재, CI 미실행, Windows 셸 부재, 대상 하드웨어 미측정, Git 이력 blob)을 우선순위와 함께 기록했다. |
| RELEASE-01 | Phase 9 / SERIAL | PASS | Main | Phase 8 Gate PASS | 자동 검사(`bash scripts/gate.sh`) 통과. 수동 검사 10항목 중 **1·3·4·5·7·8·10 완료**, 2·6 은 서버·프록시·파일시스템 범위까지 완료했다. **9와 2의 브라우저 부분은 `DEC-BROWSER-SKIP`으로 사용자가 생략을 결정했다.** Phase 3·4 의 이월된 실제 구동 검증(`DEC-RUNTIME-DEFER`: ticket 계약·셸 격리·TLS fail-closed·HTTP/8000 차단)도 이 과정에서 실제 컨테이너로 1회 수행해 해소했다. `DONE` 이 아닌 `PASS` 인 이유는 §14 릴리스 조건 "실행하지 못한 필수 검사 0건"을 문자 그대로는 충족하지 않기 때문이며, 그 차이는 사용자 결정으로 남긴다. 상세는 Validation Log 와 Known Limitations 참조. |
| AUTHZ-MATRIX-E2E | Phase 9 / RELEASE-01 선행 | DONE | Main (사용자 요청) | DOC-01 PASS, BASE-02 | RELEASE-01 수동 검사 1(권한 행렬)과 4(비활성 사용자 거부)를 자동화했다. 기존 권한 테스트는 `get_current_user`·`get_current_admin` 을 override 해 "라우트가 올바른 의존성을 선언했는가"만 증명했다. 이 검사는 override 를 전부 제거하고 `main.app` 을 그대로 띄운 뒤, 메모리 DB 에 합성 사용자를 넣고 `POST /api/auth/login` 으로 실제 토큰을 받아 계약 §2 의 21개 경로를 미인증·viewer·admin·비활성으로 호출한다. 86 PASS. |
| INACTIVE-401-FIX | Phase 3 / 사후 보정 | DONE | Main (사용자 요청) | AUTHZ-MATRIX-E2E | 위 실증에서 비활성 사용자가 21개 보호 경로 전부에서 401 대신 **403** 을 받는 것을 확인했다(계약 §1 은 401 요구). `frontend/src/api/client.js` 는 401 에서만 `onAuthExpired` 를 알리므로, 비활성화된 사용자의 세션이 정리되지 않고 토큰 만료(기본 15분)까지 "권한 부족" 화면으로 남는다. 실패 테스트 23건을 먼저 만든 뒤 `core/security.py` 의 `get_current_user` 를 401 로 바로잡고, `routers/auth.py` 로그인도 401 로 맞추면서 비활성 계정과 잘못된 비밀번호의 응답을 동일하게 만들어 계정 상태 oracle 을 없앴다. `pages/Login.jsx` 의 도달 불가능해진 403 분기를 제거했다. backend 전체 191 PASS. |
| SHELL-REST-FIX | Phase 4 / 사후 보정 | DONE | Main (사용자 승인) | SHELL-01, BASE-02 | DOC-01 준비 중 `/api/shell/reset` 과 `/api/shell/sessions` 가 서명만 확인하는 `_decode_token` 을 써서 viewer 를 막지 못하고(계약 403 요구) 비활성 사용자도 토큰 만료 전까지 통과함을 실증했다. SHELL-01 은 `/api/shell/fs` 만 DB 기반 `get_current_admin` 으로 옮겼다. 실패 테스트 5건을 먼저 만든 뒤 두 경로를 `get_current_admin` 으로 교체하고, 재발 원인인 미참조 헬퍼 `_decode_token`·`_extract_token_from_header` 와 관련 JWT import 를 제거했다. 계약 문서에 `/api/shell/sessions` 행을 추가했다(사용자 승인). focused 10 PASS, 셸 기존 17 PASS, backend 전체 105 PASS. |
| AUTHZ-02-FIX | Phase 3 / 사후 보정 | DONE | Main (사용자 승인) | AUTHZ-02, BASE-02, DEC-07 | DOC-01 준비 중 `GET /api/monitor/processes` 가 인증 없이 200 을 반환하는 것을 실증했다(BASE-02 30행은 401 요구). AUTHZ-01 은 `process.py` 의 kill 만, AUTHZ-02 는 process.py 를 소유 목록에서 제외해 두 작업 사이로 빠진 누락이다. 실패 테스트 2건을 먼저 추가해 재현한 뒤 `process` 라우터에 `dependencies=[Depends(get_current_user)]` 를 적용했다. focused 21 PASS, 재실증 401, backend 전체 95 PASS, Phase 게이트 재통과. |
| FRONT-04 | Phase 7 / Wave 7B | DONE | Main | FRONT-01, FRONT-02, FRONT-03 | 공통 `apiFetch`(JSON 파싱·Authorization·AbortController timeout 10초·`ApiError` 오류 타입)와 전역 `onAuthExpired` 401 구독을 도입해 auth/monitor/network/admin/shell/audit 호출을 한 경로로 모았다. `axios`·`chart.js`·`react-chartjs-2` 제거(6 패키지), 미사용 `styles/Users.css`·`styles/PlaceholderPage.css` 삭제. focused client 10 PASS·AuthContext 2 PASS·Phase 7 Gate 통과. |
| FRONT-03 | Phase 7 / Wave 7A | DONE | Main (사용자 승인 범위 확장) | Phase 6 Gate DONE | 정렬 머리글을 `aria-sort` + 내부 `button`으로 바꿔 키보드 정렬을 가능하게 하고(사용자 승인으로 `pages/Processes.jsx`를 범위에 포함), FileExplorer를 `tree`/`treeitem`/`group` 시맨틱과 Enter·Space 조작으로 전환, Network 탭을 `tablist`/`tab`/`tabpanel`로 교체했다. 전역 `:focus-visible`, `th scope="col"`, 로딩·오류 `role="status"`/`role="alert"`, 배열 index key 제거(pid·path·name·연결 조합 키). `vitest-axe`+`axe-core` 도입(사용자 승인)으로 6개 주요 페이지 axe 검사 + 키보드 6건 = 12 PASS. |
| FRONT-02 | Phase 7 / Wave 7A | DONE | Main | Phase 6 Gate DONE | `features/network-diagnostics/`(도구 정의·입력 검증·명령 포매팅·시뮬레이터·기록 Hook·모달)와 `features/users/`(usersApi·useUsers Hook·목록/생성/CLI/삭제 컴포넌트)로 분리. 시뮬레이션 고지 상시 표시, "실행될 명령어"→"시뮬레이션할 명령어", "실행 결과"→"시뮬레이션 결과 (실제 응답 아님)"로 실제 실행 오인 문구 제거. 셸 메타문자·비 http 스킴·bare label 거부 검증 추가. `alert()` 대신 UI 오류 표시. focused 22+8+10 = 40 PASS. |
| FRONT-01 | Phase 7 / Wave 7A | DONE | Main | Phase 6 Gate DONE | `features/filesystem/`로 가상 FS 모델(순수 함수)·권한 변환·경로 유틸·명령 기록 Hook·토스트 Hook·트리/상세/모달 컴포넌트를 분리하고 `pages/Filesystem.jsx`를 952→약 280줄 조립부로 축소. 가상 환경 고지를 페이지 상단에 상시 표시. focused 모델 20 + 페이지 10 = 30 PASS. |
| DATA-01 | Phase 6 / SERIAL | DONE | Main | PERF-02, DEC-08 | cpu/memory/disk(s)/network의 broad-except 0·빈 배열 반환을 구조화된 503(`{error:collection_failed, resource}`)으로 교체해 실제 0값과 실패를 구분. memory `buffers`/`cached`를 `getattr`로 OS 필드 차이 처리. `cleanup_old_snapshots`를 단일 SQL DELETE로 바꾸고(반환 행 수) 7일(DEC-08) 보존 job을 24시간 간격으로 스케줄러에 등록. focused 11 PASS·Gate 통과. |
| AI-NARRATE-01 | OUT_OF_PLAN_CHANGE / 사후 추가 | DONE | Main (사용자 요청) | 없음 (`docs/re-plan.md` 밖 범위, AI-NARRATE-SCOPE·AI-NARRATE-TOOLCONFIG 결정 적용) | 미지원/무관 명령(`unsupported_syntax`)에 대해 명령 실행 직후 프론트가 새 `POST /ai/sessions/{id}/commands/{attempt_id}/narrate`를 fire-and-forget으로 호출한다. **UI 배치는 사용자가 수동 테스트 중 변경을 요청해 조정함**: 터미널의 원문(`unsupported_syntax` 등)은 그대로 두고, 성공한 나레이션만 AI 도우미 패널에 `$ <명령어>` 라벨과 함께 별도 항목으로 추가한다(터미널 텍스트 교체 방식에서 전환; degraded/실패 시 도우미 패널에 아무 것도 추가하지 않음, 이전과 동일). `virtual_linux.py`/`task_grader.py`의 결정론적 상태·채점 경로는 전혀 건드리지 않음(`AICommandAttempt.narration_text` 별도 컬럼에만 기록, `grade_problem()` 시그니처에 narration 관련 파라미터 없음을 회귀 테스트로 고정). `command_parser.looks_like_shell_injection()`으로 인젝션/미매칭을 구분해 프롬프트 지시를 분기하되 둘 다 Bedrock을 호출한다(AI-NARRATE-SCOPE). `bedrock.py`에 `toolConfig` 강제 tool-use 기반 `narrate()`를 추가(AI-NARRATE-TOOLCONFIG), 기존 `tutor()`는 미변경. Alembic `0003`으로 nullable 컬럼 추가. 변경 파일: `backend/services/command_parser.py`, `backend/services/bedrock.py`, `backend/core/models.py`, `backend/migrations/versions/0003_ai_command_narration.py`, `backend/schemas/ai_tutor.py`, `backend/routers/ai_tutor.py`, `frontend/src/api/aiTutor.js`, `frontend/src/pages/AITutor.jsx`, `frontend/src/styles/AITutor.css`. 신규/확장 테스트: `backend/test/test_command_parser.py`(신규), `backend/test/test_bedrock_service.py`, `backend/test/test_ai_security.py`, `backend/test/test_ai_api.py`, `backend/test/test_task_grader.py`, `frontend/src/pages/AITutor.test.jsx`(신규, UI 배치 변경에 맞춰 갱신). |

## File Locks

PLAN-SIMPLIFY-02 이후 단일 에이전트 순차 실행으로 전환하여 파일 잠금을 사용하지
않는다. `git diff`가 곧 변경 기록이다. (과거 멀티에이전트 시절의 잠금 관리 흔적.)

## Task Packets (역사 기록 · 단일 순차 실행 이후 미사용)

아래 YAML 패킷은 모두 DONE된 작업의 기록이며 PLAN-SIMPLIFY-02가 폐기한 조율
장치다. 새 작업은 패킷을 만들지 않고 `docs/re-plan.md` §3 규칙과 §3.2 표준
게이트만 따른다. 아래는 이력 보존용으로만 남긴다.

### SHELL-02

```yaml
status: "IN_PROGRESS / Back focused test confirmed"
contract: "Shell remains current-admin only and owner-session-only; ticket is first WebSocket message, not URL. Docker run uses network none, read-only rootfs, cap-drop ALL, no-new-privileges and bounded tmpfs; backend uses only the Compose socket proxy. FS endpoint remains SHELL-01's bounded one-directory lazy tree."
ownership:
  back: ["backend/routers/shell.py", "backend/tests/test_shell_limits.py", "Dockerfile.webterm", "docker-compose.yml"]
  front_after_back_pass: ["frontend/src/components/Terminal.jsx", "frontend/src/components/FileExplorer.jsx"]
acceptance: "DONE: Back 5 focused mocked tests/compileall/Compose/static, Front lazy path fetch/merge+lint/URL-negative, independent 5 runtime-limit+7 file-tree+negative checks, and Phase 4 Gate all passed."
phase_gate: "PASS: backend 64, frontend 6, lint 0 errors/1 existing warning, build, production/dev Compose config, security scan, diff and owned whitespace passed."
```

### SHELL-01

```yaml
result: "DONE"
contract: "GET /api/shell/fs is admin-only, owner-session-only, and returns a bounded one-directory lazy tree for optional /home/user-relative absolute path."
validation:
  - "Back: pytest test_shell_file_tree.py (7 PASS); compileall (0)"
  - "Test: independent 401/403/404/owner, traversal/link/limit/nonleak PASS"
  - "Wave: python -m pytest backend/tests (59 PASS, 4 existing FastAPI deprecation warnings)"
```

### WS-01

```yaml
task_id: "WS-01"
phase: "Phase 3"
wave: "Wave 3B (serial)"
ownership:
  back: ["backend/core/security.py", "backend/routers/auth.py", "backend/routers/websocket.py", "backend/routers/shell.py", "backend/tests/test_websocket_authorization.py", "backend/tests/test_secret_logging.py"]
  front: ["frontend/src/api/client.js", "frontend/src/components/Terminal.jsx", "frontend/src/context/AuthContext.jsx"]
contract:
  - "Bearer REST issues no-store, <=60 second, one-use monitor/shell tickets."
  - "WebSockets receive the ticket only as their first authenticate message, consume it atomically, then recheck DB user activity/current role."
  - "No access token or ticket appears in WebSocket URLs or logs; monitor permits active users and shell permits current admins only."
validation:
  back: "backend focused websocket authorization + sensitive logging tests"
  front: "frontend lint after Back PASS"
  independent: "Test Agent expiry/reuse/purpose/inactive/viewer-shell/URL-negative checks"
  regression: "Wave 3B once after both implementation tracks pass"
approval: "Main approved test_secret_logging.py ownership expansion: obsolete query-JWT positive path is replaced by the fixed ticket contract; no deletion/skip/weakening."
```

### AUTHZ-01

```yaml
task_id: "AUTHZ-01"
phase: "Phase 2"
wave: "Wave 2A"
priority: "P0 / L2"
goal: "프로세스 종료를 서버 admin + demo-* 자식 프로세스로만 제한하고 viewer UI 동작을 제거한다."
evaluation_reference: ["docs/evaluation.md: 프로세스 종료 권한 불일치"]
dependencies: ["Phase 1 Gate DONE", "DEC-03 CONFIRMED"]
ownership:
  back: ["backend/routers/process.py", "backend/tests/test_process_authorization.py"]
  front: ["frontend/src/App.jsx", "frontend/src/pages/Processes.jsx", "frontend/src/pages/Processes.test.jsx"]
  pm: ["docs/re-progress.md"]
  forbidden: ["그 외 모든 파일", "AUTHZ-02 및 이후 작업"]
shared_contract:
  - "POST /api/monitor/processes/{pid}/kill: unauthenticated 401, viewer 403"
  - "admin은 이 앱이 생성·관리하는 live demo-* 서버 자식(PPID가 서버 PID)만 종료 가능"
  - "보호 PID·비자식·allowlist 밖은 403, 없는 PID는 404"
  - "계약 문서 변경 없음; 구현은 DEC-03을 그대로 따른다"
validation:
  focused: ["backend 권한 테스트 8 passed", "Processes Vitest 2 passed", "대상 ESLint 통과"]
  independent: ["Test Agent 권한 행렬 및 viewer UI 검증 PASS"]
  regression: "Phase 2 Gate PASS; lockfile 무변경으로 npm ci는 이전 설치 결과를 재사용"
risks: ["실제 프로세스 종료 금지: psutil과 child ownership은 fixture/mock으로 검증", "UI 숨김은 보조 수단이며 서버 강제가 기준"]
approval: { destructive_change: false, external_change: false }
```

### AUTHZ-02

```yaml
task_id: "AUTHZ-02"
phase: "Phase 3"
wave: "Wave 3A"
priority: "P1 / L2"
goal:
  summary: "REST 시스템 모니터링 API에 서버 인증·권한 행렬을 일관되게 적용한다."
  evaluation_reference: ["docs/evaluation.md 7.3: 시스템 정보 API 인증 누락"]
dependencies:
  completed: ["Phase 2 Gate DONE", "BASE-02 DONE"]
  decisions: ["DEC-07: 일반 모니터링은 로그인 사용자, 연결 목록은 admin"]
ownership:
  files: ["backend/routers/cpu.py", "backend/routers/memory.py", "backend/routers/disk.py", "backend/routers/network.py", "backend/routers/history.py"]
  new_files: ["backend/tests/test_monitor_authorization.py"]
  forbidden: ["그 외 모든 파일", "frontend/**", "docs/re-progress.md", "실제 SQLite DB"]
shared_contract:
  - "CPU·memory·disks·disk·history는 unauthenticated 401, viewer/admin 허용"
  - "network connections(연결·PID)은 unauthenticated 401, viewer 403, admin 허용"
  - "서버가 강제하며 프론트의 Authorization/401 흐름은 읽기 전용으로 호환성만 확인"
requirements:
  - "라우터/엔드포인트에 기존 인증 의존성을 적용하고 connections에는 admin 의존성을 적용한다."
  - "실제 시스템·DB 데이터를 fixture로 읽거나 변경하지 않고 dependency override/mock 테스트를 작성한다."
acceptance_criteria:
  - "BASE-02 모니터링 권한 행렬이 자동 테스트로 통과한다."
validation:
  focused: ["python -m pytest backend/tests/test_monitor_authorization.py"]
  regression: ["Wave 3A 완료 후 backend 전체 pytest·compileall·정적 diff/공백 검사 한 번"]
risks: ["UI는 보안 경계가 아니며, 시스템 연결·PID 정보는 admin 밖에 노출하면 안 된다."]
approval: { destructive_change: false, external_change: false }
```

### ADMIN-01

```yaml
task_id: "ADMIN-01"
phase: "Phase 3"
wave: "Wave 3A"
priority: "P2 / L2"
goal:
  summary: "DEC-02 전역 관리자 정책을 모든 사용자 CRUD에 일관되게 적용하고 마지막 활성 admin을 동시 요청에도 보존한다."
  evaluation_reference: ["docs/evaluation.md 7.13: 관리자 조회·변경 범위 불일치"]
dependencies:
  completed: ["Phase 2 Gate DONE"]
  decisions: ["DEC-02: 전역 관리자, created_by는 감사 정보"]
ownership:
  files: ["backend/routers/admin.py"]
  new_files: ["backend/tests/test_admin_scope.py"]
  forbidden: ["그 외 모든 파일", "frontend/**", "docs/re-progress.md", "실제 SQLite DB"]
shared_contract:
  - "모든 admin은 created_by와 무관하게 사용자·감사 로그 CRUD 범위를 가진다."
  - "viewer/unauthenticated는 서버에서 거부하며, self 변경 제한과 최소 한 활성 admin 보존은 유지한다."
requirements:
  - "list/create/update/delete의 predicate를 전역 admin 정책과 정렬한다."
  - "module-level asyncio.Lock 안에서 같은 AsyncSession으로 target 재조회→active admin 수→변경→commit 순으로 마지막 활성 admin 강등·비활성화·삭제를 직렬화하고 동시 요청을 테스트한다."
  - "FOR UPDATE와 BEGIN IMMEDIATE는 사용하지 않는다."
  - "임시/fixture DB만 사용하며 실제 DB, 계정, 감사 로그 값은 읽거나 변경하지 않는다."
acceptance_criteria:
  - "두 admin의 교차 CRUD가 일관되며 created_by로 제한되지 않는다."
  - "동시 강등·삭제 요청 후에도 활성 admin이 최소 한 명 남는다."
validation:
  focused: ["python -m pytest backend/tests/test_admin_scope.py"]
  regression: ["Wave 3A 완료 후 backend 전체 pytest·compileall·정적 diff/공백 검사 한 번"]
risks: ["동시성 TOCTOU와 실제 사용자·감사 데이터 노출/변경을 방지한다."]
approval: { destructive_change: false, external_change: false }
```

## Validation Log

| Task | 명령 | 결과 | 실행 환경 | 비고 |
| --- | --- | --- | --- | --- |
| BASE-01 | `python -m compileall -q main.py core routers schemas services migrations` (`backend/`) | PASS (exit 0) | Windows PowerShell | 문법 컴파일 통과 |
| BASE-01 | `python test/test_endpoints.py`, `test_websocket.py`, `test_database_integration.py` (`backend/`) | FAIL (각 exit 1) | Windows PowerShell | 기본 실행 import 오류를 기준선에 기록; 추적 DB 수정은 상태 확인 결과 없음 |
| BASE-01 | `npm ls --depth=0` 및 `npm run build` (`frontend/`) | FAIL (각 exit 1) | Windows PowerShell 및 승인된 재시도 | xterm 의존성 누락; sandbox build 권한 오류와 승인 환경의 import resolve 오류를 구분 기록 |
| BASE-01 | `docker compose config --quiet`; `git diff --check` | PASS (각 exit 0) | Windows PowerShell | Compose obsolete `version` 및 환경 경고는 제한사항으로 기록 |
| BASE-01 | 독립 Test Agent 검증 | PASS | Windows PowerShell | 문서-실행 결과 대조, DB 메타데이터만 확인, YAML 보고 수령 |
| BASE-01 | Phase 0 통합 정적 검사: `git diff --check`, `git status --short`, 프로덕션 경로 diff 확인 | PASS (exit 0) | Windows PowerShell | Phase 0에 의한 프로덕션 코드 변경 없음; 기존 사용자 변경은 보존 |
| BASE-02 | 계약 정적 대조: 권한 행렬 9행, DEC 8개, ticket·소유권·비노출 규칙 검색 | PASS | Windows PowerShell | 계약이 `docs/re-plan.md` BASE-02 표와 일치 |
| BASE-02 | 독립 Test Agent 검증 | PASS | Windows PowerShell | YAML 보고 수령: 9행·DEC 8개, 미결정/TODO/TBD 없음, 프로덕션 코드 변경 없음 |
| Phase 0 Gate | `git diff --check`; `git status --short -- backend frontend docker-compose.yml`; 기준선·계약·결정 정적 대조 | PASS (exit 0) | Windows PowerShell | DEC-01~08 CONFIRMED, BASE-01·BASE-02 DONE, Phase 0에 의한 프로덕션 코드 변경 없음 |
| Phase 0 Gate 재검증 | Main Agent `git diff --no-index --check -- NUL <untracked-doc>` 검사 | FAIL | Windows PowerShell | `docs/baseline.md` 1건, `docs/contracts/security-contract.md` 2건 trailing whitespace 발견; 일반 `git diff --check`는 미추적 파일을 검사하지 않음을 확인 |
| BASE-01 재검증 | `git diff --no-index --check -- NUL docs/baseline.md` | PASS (exit 1 해석) | Windows PowerShell | 내용 차이의 no-index exit 1, trailing whitespace/error 출력 없음; 기존 BASE-01 Test Agent PASS |
| BASE-02 재검증 | `git diff --no-index --check -- NUL docs/contracts/security-contract.md` | PASS (exit 1 해석) | Windows PowerShell | 내용 차이의 no-index exit 1, trailing whitespace/error 출력 없음; 기존 BASE-02 Test Agent PASS |
| Phase 0 Gate 재검증 | `git diff --no-index --check -- NUL docs/re-progress.md`; `rg -n "[\t ]+$"` (세 Phase 문서); `git diff --check`; scoped `git status` | PASS (각각 1, 1, 0, 0) | Windows PowerShell | 앞의 두 exit 1은 각각 no-index 내용 차이와 rg 매칭 없음이며 오류가 아님; 새 문서 포함 공백 검사 통과, 프로덕션 경로 변경 없음 |
| QA-01/QA-02 | Wave 1A 시작 전 상태·소유 범위·공유 계약 확인 | PASS | Windows PowerShell | Phase 0 Gate DONE, 파일 집합 분리, `security-contract.md` 변경 없음; 병렬 시작 |
| QA-02 | `npm --prefix frontend ci` (승인 환경) | PASS (exit 0) | Windows PowerShell | 414 packages 설치, xterm clean install 복구 |
| QA-02 | `npm --prefix frontend run lint` (승인 환경) | FAIL (exit 1) | Windows PowerShell | 기존 프로덕션 소스 ESLint error 9건·warning 2건; Front 소유 범위 밖이므로 수정·규칙 완화 없이 BLOCKED |
| QA-02 | Main Agent lint 재현 및 소유 확장 승인 | PASS | 승인된 Main 지시 | 오류 9건이 QA-02 완료에 직접 필요함을 확인; 정확한 5개 파일에만 unused/catch 문법 등 의미 보존 최소 수정 허용, FileExplorer warning 제외 |
| QA-01 | 독립 Test Agent 최초·재시도 위임 | NOT_RUN | Agent runtime | 두 시도 모두 모델 capacity 오류로 검증 명령을 실행하지 못함; QA-01은 PASS/DONE 처리하지 않고 동일 검증 재시도 중 |
| QA-01 | 독립 Test Agent 재시도 | PASS | Windows PowerShell | `pytest` 3 passed; 임시 실패 exit 1 후 삭제·재실행; compileall exit 0; 두 추적 DB hash/size/status 전후 동일 |
| QA-02 | 승인된 5개 최소 lint 수정 후 자체 검사 | PASS | 승인 환경 | `npm ci`, lint, test(4/4), build, `npm ls` 모두 exit 0; lint warning 2건은 비차단·범위 밖 |
| QA-02 | 독립 Test Agent 검증 | PASS | 승인 환경 | clean install·lint·test·build·xterm 확인, 승인 범위 5파일만 수정, FileExplorer 미수정 |
| Wave 1A 통합 | `python -m pytest backend/tests`; `python -m compileall -q backend`; 승인 환경 `npm ci/lint/test/build/npm ls`; `docker compose config --quiet`; DB status; `git diff --check` | PASS | Windows PowerShell | backend 3 passed, frontend 4 passed; 모든 필수 명령 exit 0 (sandbox npm EPERM은 승인 재시도로 구분); 추적 DB 변경 없음 |
| QA-03 | PowerShell 보안 패턴 집계 최초 시도 | NOT_RUN | Windows PowerShell | `Select-String -Recurse` 미지원으로 파일을 스캔하지 못한 false-clear를 폐기; 근거로 사용하지 않음 |
| QA-03 | `rg` 기반 비밀/JWT 로그·token URL·Nginx request log 패턴 검사 | FAIL (exit 1) | Windows PowerShell | 값은 출력하지 않음. Phase 2 범위의 기본 비밀 fallback, 민감 Python/JS log, token URL, request query log 유형이 현재 코드에서 탐지됨 |
| Phase 1 Gate | QA-01/QA-02 통합 및 QA-03 보안 scan 대조 | BLOCKED | Windows PowerShell | QA-03 CI가 현 Phase 2 결함을 실패시키며, 계획은 allowlist·완화·Phase 2 선행 수정을 금지. QA-03 workflow/Test Agent/Gate 완료 불가 |
| EXC-01 | 사용자 승인 순서 예외 및 범위 기록 | PASS | PM | SECRET-01→SECRET-02→QA-03만 허용; AUTHZ-01 및 기타 Phase 2/3 작업 금지 |
| SECRET-01 | focused/full pytest, compileall, DB hash/status, 독립 Test Agent | PASS | Windows PowerShell | focused 6 passed, full 9 passed, compileall exit 0; 추적 DB size/hash/status 전후 동일 |
| SECRET-02 | Back/Front focused·regression·독립 Test Agent | PASS | Windows PowerShell | backend focused 5/full 14 pytest, AST 0 unsafe; frontend npm lint/test/build/npm ls 및 static scan 통과; nginx -t는 도구 부재 NOT_RUN |
| QA-03 | 기존 Back Agent focused scan 2회 | NOT_RUN | Agent runtime | 두 시도 모두 60초 내 명령 결과·파일 변경 없이 중단됨. 구현 실패를 다른 Agent에게 넘긴 것이 아니라 미착수/무변경 runtime failure로 기록하고 focused scan부터 재위임. |
| QA-03 | PM 사전 scan 시도 | NOT_RUN (exit 1) | Windows PowerShell | `backend` 재귀가 기존 가상환경까지 포함해 55초 제한을 초과했다. false-clear를 폐기하며, 새 Back 담당은 명시적 소스 목록만 대상으로 재실행한다. |
| QA-03 | Main focused 보안 재검증: `python -m pytest backend/tests/test_secret_logging.py -q` | PASS (exit 0, 5 passed, 2.18s) | Main Agent / Windows PowerShell | `SECRET-01`·`SECRET-02` 범위의 비밀·민감 로그 회귀를 독립 재확인했다. Agent runtime 반복 중단 때문에 이 실행 근거로 CI workflow 작성 단계로 이동한다. |
| QA-03 | 새 Back Agent CI workflow 작성·정적 검증 시도 | NOT_RUN | Agent runtime | 60초 내 명령 결과·파일 생성 없이 중단됐다. `.github/workflows/ci.yml`는 여전히 존재하지 않으며, 구현 미착수/무변경 runtime failure다. |
| QA-03 | 독립 Test Agent workflow 검증 | FAIL | Windows PowerShell | YAML·순서·soft-failure 부재와 현재 security test(5 passed)는 통과했지만, 단일 `test_secret_logging.py`는 placeholder secret·Nginx·전체 production JWT/query/full-URL 로그와 category+path-only scan 요구를 충족하지 못했다. 동일 Back 담당 수정 필요. |
| QA-03 | 독립 Test Agent 수정 후 재검증 | FAIL | Windows PowerShell | inline scanner의 정상·placeholder·console·non-logging URL 임시 모델과 YAML은 통과했지만, `backend/main.py`, `backend/core` 전체, `backend/routers`, `backend/cli`, `frontend/src` 전체, `docker-compose.yml`을 읽지 않아 명시 production scope를 충족하지 못했다. 동일 Back 담당의 두 번째 CI 파일 수정 필요. |
| QA-03-SCAN | Back 구현 시도 1 | RUNTIME_FAILURE_NO_CHANGE | Agent runtime | 180초 구현 budget 동안 `scripts/security_scan.py`와 `backend/tests/test_security_scan.py` 파일 변경·명령 결과가 없었다. 같은 담당에 scanner 파일만 분할 재요청한다. |
| QA-03-SCAN | Back 구현 시도 2 (test file) | RUNTIME_FAILURE_NO_CHANGE | Agent runtime | `scripts/security_scan.py`는 앞선 분할 turn에서 생성·current scan PASS였으나, `backend/tests/test_security_scan.py` 전용 180초 turn은 파일 변경·명령 결과 없이 종료됐다. 두 연속 runtime failure 정책에 따라 남은 test 파일을 새 Back 담당에 재배정한다. |
| QA-03-SCAN | 재배정 Back test-file 구현 시도 1 | PARTIAL_RESULT_AFTER_INTERRUPT | Agent runtime | interrupt 직전에 `backend/tests/test_security_scan.py`가 생성된 것을 Main 확인과 PM focused pytest로 확인했다. 따라서 `RUNTIME_FAILURE_NO_CHANGE`로 확정하지 않으며 중복 skeleton 재요청을 하지 않는다. |
| QA-03-SCAN | `python scripts/security_scan.py`; `python -m pytest backend/tests/test_security_scan.py` | PASS (각 exit 0) | Windows PowerShell | current repository scan `SECURITY_SCAN_FINDINGS: 0`; focused pytest 8 passed. 실제 SQLite 값은 읽지 않았다. |
| QA-03-SCAN | 독립 Test Agent focused 검증 | PASS | Windows PowerShell | six categories의 non-zero·category/path-only·redaction, non-logging URL·제외 경로·`--root`·정확한 scope와 Back 소유 범위를 모두 실행 검증했다. |
| PLAN-SIMPLIFY-01 | `rg` 정책/순서 정적 대조, `rg -n "[\t ]+$"`, `git diff --check` | PASS (exit 0) | Windows PowerShell | AGENTS·re-plan·progress에 L0~L3, 정식 Wave 1A~1D, runtime 정책, 현재 잠금만 유지, trailing whitespace 없음 확인. Front는 L0 NOT_APPLICABLE로 Agent 미생성. |
| QA-03 | PM workflow 정적 구조 검사; `python scripts/security_scan.py`; `git diff --check` | PASS (각 exit 0) | Windows PowerShell | Python/backend→Node/npm ci→lint/test/build→Compose→scanner 순서와 soft failure 부재 확인; PowerShell YAML parser는 부재였으나 독립 Test Agent PyYAML parse PASS. |
| QA-03 | 독립 Test Agent workflow 재검증 | PASS | Windows PowerShell | PyYAML parse, 정확한 순서, no-soft-failure, scanner fixture non-zero 전파, 허용 소유 파일만 변경 확인. Hosted CI는 push 미승인으로 NOT_RUN. |
| Phase 1 Gate | `python -m pytest backend/tests`; `python -m compileall -q backend` | PASS (각 exit 0) | Windows PowerShell | backend 22 passed, compileall 통과. FastAPI `on_event` deprecation warning 4건은 비차단 제한사항. |
| Phase 1 Gate | `npm --prefix frontend ci --no-audit --fund=false`; `npm ls --depth=0`; lint; test; build | PASS (각 exit 0) | Windows PowerShell | clean install 414 packages, dependency tree 정상, lint 0 errors/2 warnings, Vitest 4 passed, Vite build 성공. |
| Phase 1 Gate | `docker compose config --quiet`; `python scripts/security_scan.py`; `git diff --check`; 단일 재귀 trailing-whitespace 검사 | PASS (각 exit 0) | Windows PowerShell | Compose config 통과(legacy `version` warning), security findings 0, diff·공백 검사 통과. |
| Phase 1 Gate | 추적 SQLite SHA-256 전후 비교 및 scoped status | PASS | Windows PowerShell | 두 DB hash가 Gate 전후 동일하고 DB git status 변경 없음; 실제 레코드는 읽지 않았다. |
| DOC-REPROGRESS-QA03 | Known Limitations 독립 검증; trailing-whitespace; `git diff --check -- docs/re-progress.md` | PASS | Windows PowerShell | 현재 제한만 유지, 역사적 실패는 Validation Log 보존, hosted CI NOT_RUN 1건, 공백 매칭 없음(exit 1)과 diff check 통과(exit 0). |
| AUTHZ-01 | Main focused: backend 권한 테스트, Processes Vitest, 대상 ESLint | PASS | Windows PowerShell | backend 8 passed, frontend 2 passed, 대상 ESLint 통과; 변경은 `process.py`, 새 backend test, `Processes.jsx`, 새 Processes test이며 `App.jsx`는 무변경 |
| AUTHZ-01 | 독립 Test Agent 권한 행렬·viewer UI 검증 | PASS | Windows PowerShell | 미인증 401, viewer 403, admin의 live app-managed `demo-*` 서버 자식만 허용, 보호·비자식·allowlist 밖 403, 없는 PID 404 및 viewer UI action 비노출 확인 |
| Phase 2 Gate | backend/frontend/Compose/scanner/diff 회귀 | PASS | Windows PowerShell | backend 30 passed(기존 경고 4), npm ls·lint(0 errors/기존 warning 2)·frontend 6 passed·build, Compose, security scan 0, diff 통과; DB 2개 status는 전후 clean, 값 미열람; npm ci는 lockfile 무변경으로 재사용 |
| AUTHZ-01 | Gate 후 owned `Processes.jsx` trailing whitespace 보정 | PASS | Windows PowerShell | 최초 Gate의 기존 공백 4건만 제거 후 대상 ESLint·2 tests·공백 및 diff 재검증 통과; 전체 Gate는 대상 코드 의미 무변경으로 반복하지 않음 |
| AUTHZ-02 | Back focused `python -m pytest backend/tests/test_monitor_authorization.py`; scoped diff | PASS | Windows PowerShell | 12 passed (1.53s), exit 0; mock psutil·fake async DB만 사용 |
| AUTHZ-02 | 독립 Test Agent focused 권한 행렬 | PASS | Windows PowerShell | 12 passed (1.51s); unauth 401, 일반 API viewer/admin 허용, connections viewer 403/admin 허용 및 실제 system/DB 미접근 확인 |
| ADMIN-01 | 최초 timeout 사후 분석 | TIMEOUT_NO_RESULT | Agent runtime | 두 shell 읽기는 0.5/0.4초 exit 0이고 편집·테스트·실행 도구는 없었다. 역사 진행 기록 과다 읽기 뒤 SQLite TOCTOU 설계를 장시간 분기한 모델 분석 지연이 확인됐다. |
| ADMIN-01 | 제한 읽기·고정 `asyncio.Lock` 설계 보정 재시도 | TIMEOUT_NO_RESULT | Agent runtime | read checkpoint 뒤 20–30초 checkpoint 요청에도 응답이 없고 60초 경계에 중단했다. `admin.py` 무변경, 새 test 파일 미생성으로 보정 후에도 결과 없는 분석 지연이 재현됐으며 추가 재시도는 금지한다. |
| ADMIN-01 | 새 Back executor 재할당 | BLOCKED | PM / agent runtime | `fork_turns=none`, worker, `gpt-5.6-terra` high 패킷으로 spawn을 시도했으나 agent thread limit으로 거부됐다. interrupted thread 재사용 금지에 따라 코드·테스트 변경과 Wave 3A 회귀는 실행하지 않았다. |
| ADMIN-01 | fresh Back executor 60초 실행 | TIMEOUT_NO_RESULT_AGENT_RUNTIME | Main / agent runtime | `fork_turns=none`의 새 terra/high worker가 고정 800단어 이하 패킷에서 60초간 tool result·파일 변경·checkpoint·test process를 만들지 못해 중단됐다. Main이 `admin.py` timestamp/length 무변경과 `test_admin_scope.py` 부재를 확인했다. old-context·reasoning·문서 과부하 완화를 모두 적용했으므로 현재 원인은 agent runtime/thread execution이며 코드·환경 실패가 아니다. 구현 잠금을 해제했고 focused·독립·Wave 3A 회귀 및 이후 Phase 작업은 NOT_RUN이다. |
| ADMIN-01 | 새 세션 Back executor 60초 경계 | TIMEOUT_NO_RESULT | PM / agent runtime | executor가 `test_admin_scope.py` 초안을 생성한 뒤 pytest·패치·명령 결과 없이 60초 경계를 초과해 Main 지시로 interrupt했다. 실제 DB는 미접근, `admin.py`는 무변경. 현재부터 stall 보정 새 context 재할당은 한 번만 허용한다. |
| ADMIN-01 | Back focused `python -m pytest backend/tests/test_admin_scope.py`; compileall·공백 검사 | PASS | Windows PowerShell | 초안의 3개 실패를 보정 후 6 passed, exit 0; `compileall` exit 0, 대상 공백 매칭 없음(`rg` exit 1). 메모리 fixture만 사용. |
| ADMIN-01 | 독립 Test Agent `python -m pytest backend/tests/test_admin_scope.py` | PASS | Windows PowerShell | exit 0, 6 passed (0.90s); auth matrix, cross-creator 전역 CRUD/audit, self·last-admin 보호 및 동시 demote/delete 보존을 독립 대조했고 파일 수정 없음. |
| Wave 3A | `python -m pytest backend/tests`; compileall; `git diff --check`; 대상 공백 검사 | PASS | Windows PowerShell | backend 48 passed, exit 0 (FastAPI deprecation warning 4); compileall/diff check exit 0, 대상 `rg` 공백 매칭 없음(exit 1). AUTHZ-02 PASS와 ADMIN-01 PASS를 DONE으로 승격. |
| WS-01 Back | `python -m pytest tests/test_websocket_authorization.py tests/test_secret_logging.py`; compileall·diff·공백 검사 | PASS | Windows PowerShell | focused 9 passed, exit 0; opaque one-use ticket, first-message authentication, DB recheck 및 ticket 로그 비노출을 검증했다. `test_secret_logging.py`는 Main 승인 범위 확장으로 obsolete query-JWT positive path를 계약에 맞춰 이관했다. |
| WS-01 Front | `npm --prefix frontend run lint`; URL credential 정적 검사 | PASS | Windows PowerShell | lint exit 0 (기존 warning 2); token/ticket query 매칭 없음(`rg` exit 1). |
| WS-01 | 독립 Test Agent focused ticket·logging·URL-negative 검증 | PASS | Windows PowerShell | backend 9 passed, exit 0; 만료·재사용·purpose·비활성·viewer shell 및 Front authenticate-first/401 정리를 독립 대조했다. |
| Wave 3B | backend pytest; frontend lint/test/build; diff·공백 검사 | PASS | Windows PowerShell | backend 52 passed, frontend lint 0 errors/기존 warning 2, Vitest 6 passed, build 통과; diff check exit 0, 대상 공백 없음. npm ci는 lockfile 무변경으로 설치 결과를 재사용했다. |
| DEPLOY-01 | Back focused production·development Compose config, `sh -n`, missing-certificate fail-closed, static·diff 검사 | PASS | Windows PowerShell | safe synthetic env에서 production/dev config exit 0, `sh -n` exit 0, 인증서 부재 production start check는 의도대로 exit 1; host `8000:8000`·top-level `version` 없음. |
| DEPLOY-01 | 독립 Test Agent 배포 경계 검증 | PASS | Windows PowerShell | production/dev config exit 0, 필수 환경 부재 config exit 1, start script·Nginx·scanner 정적 검사 통과; 실제 Docker daemon 기반 Nginx/TLS 기동은 NOT_RUN. |
| Phase 3 Gate | backend pytest; frontend lint/test/build; production·dev Compose config; security scan; compileall; diff | PASS | Windows PowerShell | 모두 exit 0: backend 52 passed, frontend lint 0 errors/기존 warning 2·Vitest 6 passed·build 통과, synthetic env Compose config, scanner 0 findings, compileall 및 diff check 통과. npm ci는 lockfile hash 무변경으로 기존 설치를 재사용했다. |
| SHELL-01 | Back focused `python -m pytest backend/tests/test_shell_file_tree.py -q`; compileall | PASS | Windows PowerShell | 7 passed, exit 0; lazy one-level listing, traversal/depth/symlink/item·size·timeout 제한과 소유 세션 검증을 격리 fixture로 확인했다. |
| SHELL-01 | 독립 Test Agent 최초 권한 음성 검사 | FAIL | Windows PowerShell | viewer가 JWT `sub`만으로 활성 shell session 파일 트리를 읽을 수 있는 계약 위반을 재현해 DONE 처리를 중단했다. |
| SHELL-01 | Back 인가 보정 및 독립 재검증 | PASS | Windows PowerShell | `get_current_admin`의 DB-current role 강제와 viewer 403 route 검사를 추가한 뒤 focused 7 passed·compileall exit 0, 독립 재검증 PASS. |
| SHELL-01 Wave | `python -m pytest backend/tests` | PASS | Windows PowerShell | backend 59 passed, exit 0; SHELL-01을 DONE으로 승격하고 잠금을 해제했다. |
| SHELL-02 | 최초 Back 및 1회 보정 Back runtime | TIMEOUT_NO_RESULT | Agent runtime | 두 executor 모두 60초 concrete-result 경계를 넘겨 중단했다. 보정 Agent의 production/test 초안은 승인 검증 없이 남았고 Front·독립 Test·Phase 4 Gate는 NOT_RUN이다. |
| SHELL-02 | Main diagnostic `python -m pytest backend/tests/test_shell_limits.py -q` | FAIL | Windows PowerShell | collection 중 `ModuleNotFoundError: fcntl`, exit 1. Windows 격리 stub과 focused 테스트 자체 수정이 완료되지 않아 구현을 PASS로 인정하지 않는다. |
| SHELL-02 resumed Back | `fork_turns=none` fixed-packet implementation | TIMEOUT_NO_RESULT | Agent runtime | 60초 동안 파일 변경·명령 결과·checkpoint가 없어 중단했다. scoped status/timestamp 확인에서 이번 executor의 변경은 없었고, focused·Compose·Front·독립 Test·Phase 4 Gate는 NOT_RUN이다. |
| SHELL-02 correction | Main `python -m pytest backend/tests/test_shell_limits.py -q` | PASS | Windows PowerShell | 앞선 no-file timeout 분류를 정정: Back의 Windows test stub·runtime patch가 반영되어 exit 0, 5 passed였다. |
| SHELL-02 Back | focused pytest; compileall; safe production/development Compose config; owned diff/공백 | PASS | Windows PowerShell | 5 passed 및 모든 정적/Compose 명령 exit 0; 실제 Docker daemon은 호출하지 않았다. |
| SHELL-02 Front | target lint; shell URL credential·공백 검사 | PASS | Windows PowerShell | lint exit 0 (기존 AuthContext warning 1), URL credential·공백 매칭 없음; one-level lazy fetch/merge만 변경했다. |
| SHELL-02 Test | limits/file-tree pytest; production/dev Compose config; static negative; diff/공백 | PASS | Windows PowerShell | 5+7 passed, Compose 및 flags/socket/ticket/lazy UI 음성 조건 통과; browser·real Docker·actual DB는 미실행. |
| Phase 4 Gate | backend pytest; frontend lint/test/build; production/dev Compose config; security scan; diff/owned whitespace | PASS | Windows PowerShell | backend 64 passed (FastAPI deprecation warning 4), lint 0 errors/기존 warning 1, Vitest 6 passed, build 통과(500kB chunk warning), Compose 2 config·scanner 0 findings·diff/공백 통과. npm ci는 lockfile hash 무변경이라 기존 Gate 설치 결과를 재사용했다. |
| PLAN-SIMPLIFY-02 | `docs/re-plan.md` 개정 후 잔재 grep(잠금/Wave/통합담당자); 후행 공백 `rg "[ \t]+$"`; `git diff --check` | PASS | Windows PowerShell (Bash tool) | 조율 절 제거 확인(남은 매치는 새 §3의 제거 설명 문장뿐), 후행 공백 0건, diff check exit 0. `re-plan.md`는 git 미추적이라 후행 공백을 직접 검사했다. 실제 코드·DB는 미변경. |
| DB-01 | `python -m pytest backend/tests/test_db_migrations.py backend/tests/test_bootstrap_security.py` | PASS (11 passed) | Windows PowerShell (Bash tool) | 빈/구/최신 DB upgrade 멱등, `created_by` 추가+데이터 보존, startup fail-closed, 반대 rename no-op을 임시 DB로 검증. 실제 추적 DB(`linux_web_gui.db`, `data/linux_web_gui.db`) 미접근. |
| DB-01 | `python -m pytest backend/tests` | PASS (70 passed, FastAPI deprecation warning 4) | Windows PowerShell (Bash tool) | 신규 migration 5 + fail-closed 부트스트랩 1 테스트 추가 후 전체 회귀 통과(기존 64 → 70). |
| DB-01 | `compileall main.py core migrations tests`; `python scripts/security_scan.py`; `docker compose config --quiet`(synthetic env); 신규/변경 파일 `rg "[ \t]+$"` | PASS (각 exit 0, scan findings 0, 공백 매칭 없음) | Windows PowerShell (Bash tool) | compose 파일은 DB-01에서 미변경이며 synthetic env로 config exit 0 재확인. Phase 5 전체 게이트(frontend lint/test/build 포함)는 REPO-01 이후 1회 실행 예정. |
| PERF-01 | `python -m pytest backend/tests/test_metrics_collector.py` | PASS (8 passed) | Windows PowerShell (Bash tool) | 공유 fan-out(50 소비자=1 수집), 브로드캐스트, 시간 기반 수집 횟수, offload 시 이벤트 루프 응답, `collect_metrics`의 `to_thread` 계약, start/stop 멱등, 스케줄러 snapshot 재사용을 검증. 전역 수집기 싱글턴 누수 방지 위해 conftest autouse `reset_collector` fixture와 부트스트랩 startup no-op stub 추가. |
| PERF-02 | `python -m pytest backend/tests/test_shell_async.py` | PASS (5 passed) | Windows PowerShell (Bash tool) | start/cleanup offload 시 루프 응답, 정리 본문 1회 실행(멱등), 동시 20스레드 스레드 안전, 취소 후 멱등 완료를 mock Docker로 검증. 실제 컨테이너 미기동. |
| DATA-01 | `python -m pytest backend/tests/test_metric_reliability.py` | PASS (11 passed) | Windows PowerShell (Bash tool) | 실제 0값(200) vs 수집 실패(503) 구분, memory OS 필드(buffers/cached) 부재·존재 처리, 빈 디스크 목록(200)과 실패(503) 구분, 7일 보존 경계·기본값·미만료 0건을 임시 in-memory DB로 검증. 실제 DB 미접근. |
| PERF-01/02 eol | `git diff --check`; raw-byte eol 확인 | PASS (exit 0) | Windows PowerShell (Bash tool) | `websocket.py`·`scheduler.py`는 인덱스가 CRLF(i/crlf)라 편집 후 `git diff --check`가 CR-at-eol을 전 줄 trailing whitespace로 오검출(exit 2)했다. 두 파일을 나머지 backend와 동일하게 LF로 정규화하고 실제 후행 공백을 제거해 exit 0. 로직 무변경(정규화 후 backend 94 passed). |
| Phase 6 Gate | `python -m pytest backend/tests`; `npm --prefix frontend run lint`; `test -- --run`; `run build`; prod/dev `docker compose config --quiet`(synthetic env); `python scripts/security_scan.py`; `git diff --check`; 신규 파일 `rg "[\t ]+$"`; 로컬 DB 해시 전후 | PASS | Windows PowerShell (Bash tool) | backend 94 passed(FastAPI deprecation warning 4); lint 0 errors/기존 warning 1; Vitest 6 passed; build 성공(500kB chunk warning); prod·dev config exit 0; scanner 0 findings; diff --check exit 0; 신규 파일 공백 없음; 로컬 DB 두 해시 전후 동일; 추적 venv/pyc/db 0건(REPO-01 유지). Phase 6는 보안 Phase가 아니므로 실제 구동 검증 불필요. npm ci는 lockfile 무변경으로 기존 설치 재사용. |
| REPO-01 | 백업(scratchpad) 동일 해시 확인; `git rm --cached` venv/pyc/db; `git ls-files` 대상 0건 검증; 단독 커밋 `5356a3b` | PASS | Windows PowerShell (Bash tool) | 사용자 승인 후 실행. 4,727건 추적 제거(venv 4,717 + pyc 8 + db 2) + `.gitignore` DB 규칙 추가, 소스 변경 0. 커밋 stat 4728 changed/7 insertions/1,419,174 deletions. 로컬 파일·DB 해시 전후 동일, 실제 레코드 미열람. 기존 사용자 스테이징 11건 커밋 제외 후 원상 복원 확인. |
| SHELL-REST-FIX | 셸 REST 3경로 × 미인증/viewer/admin 실증(임시 홈 디렉터리로 격리) | `/api/shell/reset` viewer 가 인가를 통과해 삭제 로직 진입 확인 → 수정 후 403 | Windows PowerShell (Bash tool) | 실제 `/home/webterm` 은 건드리지 않았다. 프로브에서 `/api/shell/fs` 가 viewer 401 로 나온 것은 DB 미구성에 따른 인공물이며 결함이 아님을 확인해 정정했다(SHELL-01 이 이미 403 강제). |
| SHELL-REST-FIX | `python -m pytest backend/tests/test_shell_rest_authorization.py` | 수정 전 5 FAIL → 수정 후 10 PASS | Windows PowerShell (Bash tool) | 3경로 × (미인증 401, viewer 403, DB 기반 admin 의존성 구조 검사) + 거부된 reset 이 디스크를 건드리지 않음을 임시 디렉터리로 검증. |
| SHELL-REST-FIX | `python -m pytest backend/tests`; `compileall routers/shell.py` | PASS (105 passed, exit 0) | Windows PowerShell (Bash tool) | 기존 셸 테스트 17건 회귀 없음. 미참조 헬퍼·import 제거 후 컴파일 통과. |
| DOC-01 | README 경로 ↔ OpenAPI 기계 대조 | PASS (양방향 차이 0건) | Windows PowerShell (Bash tool) | 앱 라우트에서 생성한 OpenAPI paths 와 README 표의 경로를 대조했다. 초기 대조에서 축약 표기(`/disks` · `/disk`)와 `/api/health` 누락을 발견해 전체 경로로 정정한 뒤 재대조했다. WebSocket 2경로도 기재 확인. |
| DOC-01 | 과거 보고서 줄바꿈 사고와 게이트 탐지 | PASS (복구) | Windows PowerShell (Bash tool) | 안내문을 텍스트 모드로 덧붙이다 두 파일의 CRLF 를 LF 로 바꿔 전체가 diff 로 잡혔고, 원래 있던 Markdown 강제 줄바꿈 공백 7건이 추가 줄로 오탐됐다. `scripts/gate.sh` 가 이를 잡아냈다. CRLF 를 복원해 diff 를 순수 추가 15·18줄로 되돌렸고 원본 내용은 변경하지 않았다. |
| AUTHZ-02-FIX | 인증 헤더 없는 `GET /api/monitor/processes` 실증(임시 스크립트, 스크래치패드) | 수정 전 200 → 수정 후 401 | Windows PowerShell (Bash tool) | 합성 psutil 프로세스만 사용했고 실제 호스트 프로세스·DB 는 읽지 않았다. 검증 스크립트는 프로덕션·테스트 트리에 남기지 않았다. |
| AUTHZ-02-FIX | `python -m pytest backend/tests/test_monitor_authorization.py backend/tests/test_process_authorization.py` | 수정 전 2 FAIL → 수정 후 21 PASS | Windows PowerShell (Bash tool) | `/api/monitor/processes` 를 권한 행렬 파라미터와 라우터 구조 검사에 추가했다. 기존 `test_kill_route_depends_on_admin_authorization` 은 의존성 **순서**(index 0)에 의존해 깨졌으므로, admin 요구를 유지한 채 순서 비의존으로 바꾸고 라우터 수준 로그인 요구 단언을 **추가**했다(약화 아님, 조건 1개 증가). |
| AUTHZ-02-FIX | `bash scripts/gate.sh` | PASS 10 / FAIL 0 (36s) | Windows PowerShell (Bash tool) | backend 95 passed(기존 94 + 신규 1); frontend lint·99 tests·build, prod/dev compose, scanner 0 findings, 공백 2종 통과. |
| FRONT-01 | `npm --prefix frontend test -- --run src/features/filesystem src/pages/Filesystem.test.jsx` | PASS (30 passed) | Windows PowerShell (Bash tool) | 분리 전 실패 테스트를 먼저 작성해 모듈 부재로 8건 실패를 확인한 뒤 구현했다. 모델 순수성(입력 트리 불변), mkdir/touch/rm/nano/mv/chmod 명령 문자열과 한국어 오류 메시지, 교육용 동작(중복 거부·삭제·권한 표기)과 가상 환경 고지 상시 표시를 검증했다. |
| FRONT-02 | `npm --prefix frontend test -- --run src/features/network-diagnostics src/pages/NetworkDiagnostics.test.jsx src/pages/Users.test.jsx` | PASS (40 passed) | Windows PowerShell (Bash tool) | 검증 12 + 시뮬레이터/명령 10 + 진단 페이지 8 + 사용자 CRUD 10. `google.com; rm -rf /`·`file:///etc/passwd`·`localhost` 거부와 실행 오인 문구 부재를 확인했다. 사용자 CRUD는 usersApi를 mock 해 실제 서버·DB에 접근하지 않았다. |
| FRONT-03 | `npm --prefix frontend test -- --run src/test/accessibility.test.jsx` | PASS (12 passed) | Windows PowerShell (Bash tool) | 수정 전 실행에서 axe 페이지 검사 6건은 이미 통과하고 키보드·시맨틱 6건이 실패함을 확인했다(axe 단독으로는 div onClick 을 잡지 못함). 수정 후 Dashboard·Processes·Filesystem·NetworkDiagnostics·Network·Users axe serious/critical 0건, 정렬 aria-sort·키보드 정렬·행-프로세스 결속·tablist 전환·tree focus/Enter/Space 통과. |
| FRONT-04 | `npm --prefix frontend test -- --run src/api/client.test.js src/test/AuthContext.test.jsx` | PASS (12 passed) | Windows PowerShell (Bash tool) | apiFetch 의 JSON 파싱·베이스 경로·Bearer 부착(auth:false 제외)·빈 본문 null·ApiError status/detail·FastAPI detail 배열 평탄화·비 JSON fallback·timeout abort 를 검증했다. 401 은 구독자 전원에게 1회 알리고 구독 해제가 동작하며 로그인 실패는 만료로 보지 않음을 확인했다. AuthContext 가 전역 401 알림으로 세션을 정리하는 경로를 추가 검증했다. |
| FRONT-04 | 미사용 의존성·스타일 확인 후 제거 | PASS | Windows PowerShell (Bash tool) | `axios`·`chart.js`·`react-chartjs-2` 를 import 하는 소스가 0건임을 확인 후 uninstall(6 패키지 제거). `styles/Users.css`·`styles/PlaceholderPage.css` 가 어디에서도 import 되지 않음을 확인 후 삭제. 제거 후 남은 CSS 전부 import 확인, 남은 dependencies 6개 모두 사용 중. |
| FRONT-04 | 번들 크기 비교 | PASS (변화 없음) | Windows PowerShell (Bash tool) | 제거 전후 build 산출물이 동일했다(`index-BnanKVZz.js` 949.75 kB / gzip 264.85 kB, CSS 64.46 kB). 세 의존성은 이미 어떤 소스도 import 하지 않아 번들에 포함되지 않았으므로 제거 효과는 설치 용량(6 패키지)에만 있다. 500 kB 초과 chunk 경고는 recharts·xterm 때문이며 Phase 1 기준선과 동일하게 남아 있다. |
| Phase 7 Gate | `python -m pytest backend/tests`; `npm --prefix frontend ci --no-audit --fund=false`; `run lint`; `test -- --run`; `run build`; prod/dev `docker compose config --quiet`(synthetic env); `python scripts/security_scan.py`; `git diff --check`; 신규 파일 `rg "[\t ]+$"` | PASS | Windows PowerShell (Bash tool) | backend 94 passed(FastAPI deprecation warning 4); clean install 412 packages; lint 0 errors/기존 warning 1; Vitest 99 passed(6 → 99); build 성공(500 kB chunk warning); prod·dev config exit 0; scanner 0 findings; diff --check exit 0; 신규 파일 공백 매칭 없음. Phase 7 은 보안 Phase 가 아니므로 실제 구동 검증 불필요. lockfile 이 바뀌어 `npm ci` 를 1회 실행했다. |
| FRONT-03 eol | `git diff --check`; 인덱스 blob 줄바꿈 확인 | PASS (exit 0) | Windows PowerShell (Bash tool) | `frontend/src/styles/Processes.css` 는 인덱스 blob 이 CRLF 인 anomaly 라 추가한 23줄의 CR 이 후행 공백으로 오검출됐다(exit 2). 실제 후행 공백은 0건임을 diff 원문으로 확인한 뒤 Phase 6 의 `websocket.py`·`scheduler.py` 와 같은 방식으로 파일 전체를 LF 로 정규화해 exit 0. 줄바꿈을 무시한 내용 비교에서 추가 23줄·삭제 0줄로 로직 변경이 없음을 확인했다. |
| Phase 5 Gate | `python -m pytest backend/tests`; `npm --prefix frontend run lint`; `test -- --run`; `run build`; prod/dev `docker compose config --quiet`(synthetic env); `python scripts/security_scan.py`; `git diff --check`; 신규 파일 `rg "[\t ]+$"`; 로컬 DB 해시 전후 | PASS | Windows PowerShell (Bash tool) | backend 70 passed(FastAPI deprecation warning 4); lint 0 errors/기존 warning 1; Vitest 6 passed; build 성공(500kB chunk warning); prod·dev config exit 0; scanner 0 findings; diff --check exit 0(LF→CRLF는 정보 경고); 신규 파일 공백 매칭 없음; 로컬 DB 두 해시 전후 동일. npm ci는 lockfile 무변경으로 기존 설치 재사용. |
| AUTHZ-MATRIX-E2E | `python -m pytest backend/tests/test_authorization_matrix_e2e.py` (수정 전) | FAIL (21 failed, 64 passed) | Windows PowerShell (Bash tool) | 미인증 21행 401, viewer 21행, admin 21행은 전부 계약대로였다. 비활성 사용자 21행이 모두 실패했고 실제 응답은 403 이었다. override 없는 실제 의존성 체인·실제 로그인 토큰 기준이다. |
| INACTIVE-401-FIX | `python -m pytest backend/tests/test_authorization_matrix_e2e.py` (수정 후) | PASS (86 passed) | Windows PowerShell (Bash tool) | 비활성 21행이 401 로 바뀌었고, 로그인이 비활성 계정과 잘못된 비밀번호에 같은 상태 코드·같은 본문을 반환함을 확인했다. |
| INACTIVE-401-FIX | `python -m pytest backend/tests` | PASS (191 passed) | Windows PowerShell (Bash tool) | 105 → 191. 401 로의 변경에 대한 회귀 0건이며, 기존에 비활성 사용자 403 을 단언하던 테스트는 없었다. |
| STUDY-01 | 인용 경로 실증: `python -m pytest <9개 파일> --collect-only -q` | PASS (141 collected) | Windows PowerShell (Bash tool) | 튜토리얼이 "완료 테스트"로 제시한 9개 테스트 경로가 모두 실제로 수집된다. 인용한 파일 경로(`Dockerfile.webterm`은 저장소 루트)와 수치(`MAX_SHELL_SESSIONS_PER_USER=1`, `MAX_SHELL_SESSIONS_GLOBAL=5`, 운영 compose backend 는 `expose` 만 사용)도 코드와 대조했다. |
| RELEASE-01 #7 | 실제 DB 복사본 대상 `alembic upgrade head` / `downgrade base` | PASS | Windows PowerShell (Bash tool) | 로컬 실 DB 2개를 sha256 기록 후 스크래치패드로 복사해 복사본에서만 실행했다. upgrade 는 멱등적이었다(테이블 3개 유지, 행 수 42/7960/11 전후 동일, `alembic_version`=0001 스탬프, `web_users.username` 유지=DEC-01). 별도 복사본에서 `downgrade base` 는 exit 0 으로 완료되며 테이블 3개를 drop 한다(초기 리비전이므로 설계상 데이터 삭제이며 `docs/db-operations.md` 가 이미 경고한다). 실행 후 원본 2개 sha256 이 실행 전과 동일함을 확인했다. 실제 레코드는 읽지 않고 행 수와 컬럼명만 확인했다. |
| RELEASE-01 #3·4·8 + ticket 계약 | 실 uvicorn(127.0.0.1:8123, 임시 DB, 합성 계정 3개) 대상 httpx·websockets 클라이언트 13개 검사 | PASS (13/13) | Windows PowerShell (Bash tool) | #3 viewer kill 403·미인증 401. #4 비활성 사용자 REST 401·ticket 발급 401·로그인 401. ticket 계약(Phase 3 실제 구동 이월분): `Cache-Control: no-store`, `expires_in_seconds`=60, 최초 사용 수락, **재사용 거부**, monitor ticket 으로 `/ws/shell` 연결 **거부**, 인증 메시지 전 데이터 미전송. #8 모니터링 WebSocket **50/50** 동시 연결이 첫 데이터까지 5.2초, 연결 유지 중 REST 200(1109ms). |
| RELEASE-01 #2 | 실 서버 로그(37,150자) 대상 실제 발급값 대조 | PASS (노출 0건) | Windows PowerShell (Bash tool) | 패턴 추정이 아니라 이번 실행에서 실제로 발급된 access token 2개(149·152자)와 ws ticket 2개(43자)의 **원문 문자열**이 로그에 있는지 대조해 4건 모두 부재를 확인했다. URL 쿼리 `?token=`/`?ticket=` 0건, `Bearer ` 0건, SECRET_KEY 값·합성 비밀번호 노출 없음. Nginx 액세스 로그와 브라우저 콘솔은 Docker·브라우저가 필요해 미실행. |
| RELEASE-01 #6 | `python -m pytest backend/tests/test_shell_file_tree.py -v -rs` | PASS (7 passed, 0 skipped) | Windows PowerShell (Bash tool) | 이 환경은 심볼릭 링크 생성이 가능해 `pytest.skip` 경로가 타지 않았다. 즉 밖을 가리키는 심볼릭 링크 제외·링크 대상 거부·순환 링크 제외가 **실제 파일시스템 링크로** 검증됐다. 실 HTTP 라우트 + 실 셸 세션 조합은 Docker 가 필요해 미실행. |
| RELEASE-01 #10 (부분) | `frontend/start.sh` fail-closed 실행 | PASS | Windows PowerShell (Bash tool) | `DOMAIN_NAME` 미설정 exit 1, 운영 모드에서 인증서 파일 부재 exit 1(`nginx -t` 이전에 중단). 운영 compose 의 backend 는 `expose` 만 사용해 호스트 포트 바인딩이 없음을 config 로 확인했다. 실제 컨테이너 기동 후 HTTP→HTTPS 리다이렉트와 8000 직접 접근 차단은 Docker 가 필요해 미실행. |
| RELEASE-01 #5 | `webterm:latest` 빌드 후 `shell.py` 와 동일한 격리 플래그로 컨테이너 기동, 내부 probe 18항목 | PASS (18/18) | Docker 29.3.1 (linux/amd64) | 이미지가 없어 `Dockerfile.webterm` 으로 먼저 빌드했다. 네트워크: ping·DNS·HTTP 아웃바운드 전부 실패, 인터페이스 `lo` 만 존재. Docker: `/var/run/docker.sock` 부재, `docker` CLI 부재. 파일시스템: `/etc`·`/usr/bin` 쓰기 거부, 홈만 rw, `/tmp` noexec 로 스크립트 실행 거부. 권한: `NoNewPrivs=1`, `CapEff=0000000000000000`, `su root` 거부, uid/gid 1000. 한도: 메모리 268435456 bytes, pids 100. pty(`os.setsid`)가 POSIX 전용이라 셸 세션 전체 흐름이 아닌 컨테이너 격리 속성만 검증했다. |
| RELEASE-01 #10 | 운영 compose 프로필 실제 기동(임시 override: 실 DB 마운트를 빈 임시 DB 로 대체, certbot 미기동) | PASS | Docker 29.3.1 | 인증서 없이 기동 시 frontend 가 `Exited (1)` 로 **fail-closed**(로그: "Production requires TLS certificate files")—DEC-05 실증. 임시 자체 서명 인증서 투입 후 정상 기동(`nginx -t` 통과). HTTP `/` → **301** `https://`, `/api/health` 도 301, HTTPS 200. 보안 헤더 4종(HSTS max-age=31536000·nosniff·X-Frame-Options DENY·Referrer-Policy) 확인. backend 는 `PortBindings={}` 로 호스트 게시가 전혀 없어 8000 직접 접근이 구조적으로 불가함을 `docker inspect` 로 확정했다. 검증 후 스택 제거와 임시 인증서 삭제를 완료했다(남은 인증서 디렉터리 0). |
| RELEASE-01 #2 (Nginx) | 프록시 경유 실제 트래픽 후 nginx 액세스 로그 대조 | PASS (노출 0건) | Docker 29.3.1 | HTTPS 로 register→login→인증 요청→ticket 발급을 수행해 실제 토큰(151자)을 발급받은 뒤, nginx 로그 18줄 전체에서 **토큰 원문 부재**, URL 쿼리 `token=`/`ticket=` 0건, `Bearer` 0건, `Authorization` 0건, 비밀번호 노출 없음을 확인했다. |
| Phase 8 Gate | `bash scripts/gate.sh` + 문서 명령 실행 가능·실제/시뮬레이션 구분·README와 OpenAPI 경로 일치 | PASS (10/0, 104s) | Windows PowerShell (Bash tool) | backend 191 passed; npm ci·lint·Vitest·build PASS; prod·dev compose config PASS; security scan 0 findings; 공백 위반 0건. 나머지 세 조건은 DOC-01(OpenAPI 양방향 차이 0건, 시뮬레이션 고지 상시 표시)과 STUDY-01(인용 경로 141건 수집)에서 각각 확인했다. DOC-01·STUDY-01 을 DONE 으로 승격했다. |
| Phase 9 선행 Gate | `bash scripts/gate.sh` | PASS (10/0, 107s) | Windows PowerShell (Bash tool) | backend 191 passed; npm ci·lint·Vitest·build PASS; prod·dev compose config PASS; security scan 0 findings; 추적 diff·미추적 파일 공백 위반 0건. Phase 3·4 실제 구동 검증은 RELEASE-01 로 이월된 상태 그대로다. |
| AI-NARRATE-01 | `python -m pytest backend/tests -q` (신설 venv, `backend/venv`+`.venv`는 인터프리터 바이너리가 없어 재사용 불가해 scratchpad에 `requirements.txt` 그대로 재설치) | PASS (196 passed) | Linux sandbox (Bash tool) | 이번 변경 전 베이스라인도 동일 196 passed로 동일 환경에서 먼저 확인, 회귀 없음. |
| AI-NARRATE-01 | `backend/test/*.py` 6개 레거시 스크립트 직접 실행(`python test/test_command_parser.py` 등, `docs/evaluation.md:207`대로 pytest collection 대상 아님) | PASS (6/6) | Linux sandbox | `test_command_parser.py`(신규), `test_virtual_linux.py`, `test_task_grader.py`, `test_bedrock_service.py`, `test_ai_api.py`, `test_ai_security.py`. narrate 관련 신규 케이스: toolConfig 성공/스키마위반/재시도/비밀로그미노출, 인젝션/미매칭 분기, state_json·version 불변, 소유권 404, success attempt 400, 미지원 attempt_id 404, degraded 폴백 시 원문 유지. |
| AI-NARRATE-01 | `npx vitest run` (frontend, `npm ci` 선행 — node_modules에 vitest 바이너리 누락 상태였음) | PASS (12 files, 102 tests) | Linux sandbox | 신규 `AITutor.test.jsx` 3건 포함(원문 즉시 표시 후 나레이션 교체, degraded 시 원문 유지, success 명령은 narrate 미호출). |
| AI-NARRATE-01 | `bash scripts/gate.sh` (venv `bin/`을 PATH에 추가해 `python` 바이너리 확보) | 9 PASS / 1 FAIL (137s) | Linux sandbox | `frontend lint`만 실패. 원인은 `frontend/src/utils/terminalSafety.js`의 기존 `no-control-regex`/`no-useless-escape` 6건으로, `git status`로 이 파일이 이번 작업에서 전혀 건드리지 않은 상태(HEAD와 diff 0)임을 확인한 **작업 범위 밖 선행 실패**다. 나머지 backend pytest·frontend test/build·compose config(운영/개발)·security scan·공백 검사(추적/미추적) 9건은 모두 PASS. |
| AI-NARRATE-01 | 실제 구동 검증: 임시 sqlite DB로 `uvicorn main:app` 기동 → `alembic upgrade head`가 0001→0002→0003(신규 마이그레이션) 자동 적용 확인 → 실 HTTP로 register/login/session 생성/command/narrate 전체 흐름 | PASS | Linux sandbox, 실 AWS Bedrock 호출 포함(아래 특이사항 참고) | 세션·명령 실행·narrate 200(실제 Bedrock 응답, 아래 참고)·narration_text가 `/history`에 영속 확인·success attempt narrate 400·미지원 attempt_id 404·다른 사용자 소유 attempt narrate 404를 모두 실 HTTP 요청/응답으로 확인. 검증 후 프로세스 종료, 임시 DB·응답 파일 삭제. |
| AI-NARRATE-01 | UI 배치 변경(사용자 요청, 터미널 교체→AI 도우미 패널 별도 항목) 후 `npm --prefix frontend test -- --run AITutor`, `npm --prefix frontend run lint` | PASS (3/3), lint AITutor 관련 신규 오류 없음 | Linux sandbox | `AITutor.test.jsx` 3건을 새 배치에 맞춰 갱신(터미널은 원문 유지 확인, 도우미 패널에서 `$ <명령어>` 라벨과 나레이션 텍스트 확인, degraded 시 도우미 패널에 미추가 확인). 백엔드는 변경 없음(narrate 응답 스키마 그대로, 배치는 순수 프론트 렌더링 문제). |
| AI-NARRATE-01 | 버그 수정: 사용자가 실제 수동 테스트 중 `ls -al`(파서가 지원하는 `ls`/`ls /경로` 형태가 아니라 unsupported_syntax) 입력 시 AI 나레이션이 `'ls: 명령어를 찾을 수 없습니다'`(사실과 다름 — `ls`는 시뮬레이터가 지원하는 명령어이고 `-al` 플래그 조합만 미지원)를 지어낸 것을 발견. `backend/services/bedrock.py`의 `_UNMATCHED_INSTRUCTION`이 모델에게 거부 사유(명령어 자체 미지원 vs 인자 미지원)를 전혀 안 줘서 모델이 구체적 기술적 사유를 임의로 지어낼 수 있었던 게 원인. 실패 테스트 먼저(`test_bedrock_service.py::test_narration_prompt_boundary_and_rejection_kind`에 `'does not exist'`/`'is not found'` 가드레일 문구 부재 확인) → `_UNMATCHED_INSTRUCTION`에 "구체적 기술적 사유(존재하지 않음/찾을 수 없음 등)를 절대 단정하지 말고, 중립적으로 '이번 학습 단계에서는 지원되지 않는 입력'이라고만 안내하라"는 지시 추가 → 통과. | PASS | Linux sandbox | `test_bedrock_service.py` 14/14, `backend/test/*.py` 6개 레거시 스크립트 6/6(회귀 없음) 전부 PASS. 이 수정은 프롬프트 지시문 텍스트만 바꾼 것이라 실제 모델 응답 품질 변화는 mock 기반 단위 테스트로는 보장 못 함 — 다음 실 Bedrock 호출 시 육안 확인 필요(알려진 한계로 기록). |

## Known Limitations

- 실제 SQLite 레코드, 사용자명, IP, 비밀 및 토큰은 읽거나 기록하지 않는다.
- 작업 시작 전부터 있던 사용자 변경(AGENTS 수정, 기존 문서 삭제, 계획·평가 문서 추가 등)은 보존하며 계획 변경과 구분한다.
- 일반 `git diff --check`는 미추적 Phase 산출물을 검사하지 않는다. PLAN-SIMPLIFY-01 이후 Wave/Gate는 `git diff --check`와 대상 새 파일의 단일 재귀 trailing-whitespace 검사로 함께 확인한다.
- npm audit은 clean install 검증과 분리한다. `--no-audit --fund=false` 사용은 취약점 발견을 보장하지 않으므로 별도 audit이 실행되기 전까지 제한사항이다.
- GitHub hosted CI는 push가 승인되지 않아 NOT_RUN이다. 로컬 동등 명령과 독립 workflow 구조 검증으로 대체했다.
- lint는 오류 없이 통과했으나 기존 React Hook/Fast Refresh warning 1건이 남아 있고, build에는 500 kB 초과 chunk 경고가 있다.
- DEPLOY-01은 Compose 정적 구성과 인증서 부재 fail-closed 스크립트를 검증했지만 실제 Docker daemon 기반 Nginx/TLS 컨테이너 기동은 실행하지 않았다.
- 개발 override도 production base의 필수 환경변수 보간을 상속하므로 Compose config 실행에는 안전한 개발용 환경값이 필요하다.
- backend test는 FastAPI `on_event` deprecation warning 4건을 출력한다. 기능 실패는 아니다.
- ADMIN-01 마지막 활성 admin 보장은 단일 프로세스의 module-level `asyncio.Lock` 범위다. 다중 프로세스/다중 인스턴스 배포에는 분산/DB 수준 직렬화가 필요하며, 현재 범위에서는 사용하지 않는다.
- SHELL-02는 mocked/static 검증과 Compose config를 통과했지만 실제 Docker daemon·컨테이너 런타임 및 browser 상호작용은 실행하지 않았다.
- SHELL-02의 사용자별·전체 세션 한도는 단일 backend 프로세스의 메모리 상태 기준이다. 다중 worker·다중 인스턴스 배포에는 공유 세션 한도 저장소가 필요하다.
- DB-01: 앱은 startup 시 `alembic upgrade head`(fail-closed)로 스키마를 적용한다. `alembic==1.13.2`가 requirements에 추가됐고 Dockerfile `COPY . .`로 `alembic.ini`·`migrations/`가 이미지에 포함된다. 마이그레이션 실행 위치는 별도 entrypoint 없이 uvicorn 단독 기동 구조에 맞춰 startup 이벤트로 선택했다.
- DB-01: `cli/create_admin.py`는 여전히 `create_all`로 테이블을 만든다(현재 모델과 동일 스키마라 호환). 이후 앱 첫 기동 시 멱등 리비전 `0001`이 기존 테이블은 건드리지 않고 alembic_version만 스탬프한다.
- DB-01은 임시/복사 DB로만 검증했고 실제 운영 DB(`data/linux_web_gui.db`) upgrade는 실행하지 않았다. 실운영 적용은 `docs/db-operations.md`의 백업·검증(복사본 리허설)·복구 절차를 따른다.
- REPO-01은 `git rm --cached`로 추적만 제거했고 로컬 워킹트리 파일(venv, 실행 DB)은 삭제하지 않았다. 두 실행 DB는 세션 scratchpad에 동일 해시로 백업했으며 이는 세션 임시 저장소이므로 영속 백업이 필요하면 사용자가 별도 위치로 보관해야 한다. Git 이력에는 과거 커밋의 blob이 그대로 남아 있어(이력 재작성은 계획 범위 밖) 이미 push된 기록에서 값을 제거하려면 별도 결정·승인이 필요하다.
- REPO-01 커밋(`5356a3b`)은 main 브랜치의 dirty worktree 위에 인덱스 기반으로 만들어졌다. 프로젝트가 Phase 전반을 커밋 없이 dirty worktree로 운영해 왔기에 별도 브랜치 없이 진행했고, 사용자의 기존 스테이징(`.codex/*`, `AGENTS.md` 삭제 11건)은 커밋에서 제외한 뒤 원상 복원했다.
- PERF-01: 단일 수집기와 부하 검증은 결정적 유닛 테스트(주입형 fake·offload 계약·시간 기반 수집 횟수)로 확인했다. 실제 50개 WebSocket 동시 연결·실 psutil 부하의 이벤트 루프 지연 측정은 실행하지 않았다(mocked/deterministic 검증). 수집기는 연결 여부와 무관하게 5초마다 항상 수집한다(계획된 상시 수집기 설계).
- PERF-02: 셸 offload·정리 1회 실행은 mock Docker로 검증했고 실제 컨테이너 런타임은 기동하지 않았다. `_cleaned`는 프로세스 내 `threading.Lock` 범위이며, 다중 인스턴스 배포에는 적용되지 않는다.
- DATA-01 API 계약 변경: cpu/memory/disk(s)/network 수집 실패가 이전의 200+0값/빈 배열 대신 **HTTP 503**(`{"error":"collection_failed","resource":...}`)을 반환한다. 권한 행렬(401/403/200)은 불변이며 성공 응답 스키마도 불변이다. 프론트엔드의 503 처리·표시는 Phase 7/DOC-01 범위이며 아직 반영하지 않았다.
- DATA-01 보존 job(`snapshot_retention_job`)은 24시간 간격으로 등록됐고 경계·기본값·미만료 케이스를 임시 in-memory DB(StaticPool)로 검증했다. 실제 운영 DB 대상 보존 실행은 하지 않았다.
- 게이트 실행기 `scripts/gate.sh`를 추가했다(사용자 승인, re-plan 작업 아닌 도구). §3.2 표준 게이트 명령과 Compose 합성 환경값, npm ci 재사용(lockfile 해시), 줄바꿈과 무관한 공백 검사를 한 번의 실행으로 묶는다. 기존 게이트보다 넓다: `git diff --check`가 보지 못하는 **미추적 파일**까지 검사하고, 추적 diff와 미추적 파일을 나눠 보고해 원인을 구분한다. 실제 위반 탐지력은 검증했다(추적 CRLF 파일·미추적 파일 양성 검사, ignore 목록이 다른 파일을 덮지 않는 음성 검사). 보안 Phase의 실제 구동 검증은 대체하지 않는다.
- `scripts/gate-whitespace-ignore.txt`에 `docs/evaluation.md` 1건이 있다. Phase 7 시작 전부터 있던 사용자 소유 미추적 문서이며 3행 끝 공백 2칸은 Markdown 강제 줄바꿈일 수 있어 파일을 수정하지 않고 범위 밖으로 표시했다. 사용자가 원하면 항목을 지우고 해당 문서의 후행 공백을 제거하면 된다.
- FRONT-03: `vitest-axe`와 `axe-core`를 devDependency로 추가했다(사용자 승인). 계획상 `package.json`·`package-lock.json`은 FRONT-04 소유였으나 FRONT-03의 "자동 접근성 검사" 완료 조건을 충족하려면 필요했다. axe 게이트는 `serious`/`critical` 위반 0건 기준이며, axe 단독으로는 클릭 가능한 `div` 같은 문제를 잡지 못하므로 키보드 조작 단언을 함께 둔다.
- FRONT-03: 정렬 머리글이 있는 `pages/Processes.jsx`는 계획의 FRONT-03 소유 목록에 없었으나 `aria-sort` 요구를 실제로 충족하려면 필요해 사용자 승인 하에 범위에 포함했다.
- FRONT-03: 접근성 검증은 jsdom + axe 정적 검사와 합성 이벤트 기반이다. 실제 브라우저의 스크린리더 낭독, 초점 순서 육안 확인, 반응형 표의 실제 가로 스크롤 동작은 실행하지 않았다.
- FRONT-04: 세 의존성 제거로 번들 크기는 변하지 않았다(제거 전후 산출물 해시 동일). 이미 어떤 소스도 import 하지 않던 의존성이라 효과는 설치 용량에만 있다. 500 kB 초과 chunk 경고는 `recharts`와 `@xterm/xterm` 때문이며 그대로 남아 있다.
- FRONT-04: `apiFetch`의 기본 timeout은 10초다. WebSocket 경로(`wsManager`)는 이 계층을 쓰지 않고 기존 ticket 흐름을 유지한다.
- `frontend/src/styles/Processes.css`는 인덱스 blob이 CRLF였던 anomaly라 FRONT-03에서 LF로 정규화했다(나머지 frontend와 일치). `git diff`에서 줄바꿈 변경으로 크게 보이지만 줄바꿈을 무시한 내용 비교에서 추가 23줄·삭제 0줄로 스타일 로직 변경은 없다. `core.autocrlf=true`가 다음 체크아웃 시 CRLF로 되돌릴 수 있다.
- `backend/routers/websocket.py`·`backend/services/scheduler.py`는 인덱스가 CRLF였던 anomaly라 Phase 6에서 LF로 정규화했다(나머지 backend와 일치). 이로 인해 두 파일은 `git diff`에서 줄바꿈 변경으로 크게 보일 수 있으나 로직 변경은 없다. `core.autocrlf=true`가 다음 체크아웃 시 CRLF로 되돌릴 수 있다.
- AUTHZ-MATRIX-E2E는 REST 권한 행렬만 자동화한다. WebSocket(`/ws/monitor`·`/ws/shell`)의 비활성 사용자 거부는 `test_websocket_authorization.py`가 따로 다루며, 이 검사에는 포함되지 않는다.
- AUTHZ-MATRIX-E2E의 "허용"은 `401`·`403`이 아님을 뜻한다. 수집 실패 503이나 psutil OS 차이로 인한 5xx는 권한과 무관한 별개 관심사이므로 이 검사에서 구분하지 않는다.
- AUTHZ-MATRIX-E2E는 `TestClient`를 컨텍스트 매니저로 쓰지 않아 startup 이벤트(도커 이미지 조회, alembic 마이그레이션, 스케줄러·수집기 기동)를 실행하지 않는다. 라우팅·의존성·인증 체인은 실제 앱 그대로지만, 기동 시퀀스 자체는 RELEASE-01 실제 구동 검증의 몫이다.
- INACTIVE-401-FIX로 로그인은 비활성 계정과 잘못된 비밀번호를 구분하지 않는다. 비활성화된 사용자는 로그인 화면에서 이유를 알 수 없으며 관리자가 별도로 알려야 한다. 계정 상태 노출을 막기 위한 의도된 선택이다.
- STUDY-01은 계획이 소유 파일로 지정한 `docs/LEARNING_LOG.md`의 템플릿 부분을 수정하지 않았다. 해당 파일은 작업 시작 전부터 있던 사용자 소유 미추적 문서이고, 이미 사용자가 작성한 이해도 척도(L0~L4)·주제별 상세 템플릿·세션 로그 템플릿이 들어 있다. 기존 사용자 문서를 덮어쓰지 않는다는 규칙에 따라 `docs/tutorials/README.md`에서 이 파일을 기록 위치로 가리키는 데 그쳤다. 템플릿 변경이 필요하면 사용자 승인 후 별도로 처리한다.
- STUDY-01은 사용자 결정에 따라 계획 원안(7개 과제 전체 튜토리얼)보다 축소된 형태다. 6개 필수 요소는 모두 유지했으나 실패 테스트를 코드가 아닌 명세로 제시하므로, 학습자가 직접 작성하지 않으면 그 부분은 검증되지 않는다.
- RELEASE-01 수동 검사 5(셸 네트워크·Docker 접근 차단)는 Docker 데몬이 실행되지 않아 `NOT_RUN`이다. 10(운영 프로필 HTTP·8000 직접 접근 차단)은 정적 구성과 fail-closed 스크립트까지만 확인했고 실제 컨테이너 기동은 `NOT_RUN`이다.
- RELEASE-01 수동 검사 2는 backend 서버 로그만 실증했다. Nginx 액세스 로그와 브라우저 콘솔·네트워크 탭은 각각 Docker와 실제 브라우저가 필요해 `NOT_RUN`이다.
- RELEASE-01 수동 검사 9(키보드 기반 주요 화면 사용)는 FRONT-03의 jsdom + axe + 합성 키 이벤트 검증이 전부다. 실제 브라우저의 초점 순서·스크린리더 낭독은 여전히 `NOT_RUN`이다.
- RELEASE-01 수동 검사 4의 WebSocket 경로는 "비활성 사용자는 ticket 자체를 발급받지 못한다"(401)로 확인했다. 활성 상태에서 ticket을 받은 직후 계정이 비활성화된 뒤 그 ticket으로 연결하는 경로는 실제 구동으로 검증하지 않았다. 해당 재확인 로직은 `test_websocket_authorization.py`의 단위 검증 범위다.
- RELEASE-01 실제 구동 검증은 Windows 개발 호스트에서 수행했다. 50개 WebSocket 부하 중 REST 응답이 1,109ms로 측정됐는데, 이는 대상 배포 환경(라즈베리 파이/리눅스 컨테이너)의 수치가 아니며 부하 판정 기준으로 쓸 수 없다.
- 검증 스크립트가 발급 토큰 대조용 임시 파일을 저장소 안(`backend/secrets.txt`)에 생성해 즉시 스크래치패드로 옮겼다. `git status`에 흔적이 없음을 확인했다. 검증 산출물은 저장소 밖에 두어야 한다.
- RELEASE-01 #5·#10 을 Docker 로 완료해, 앞서 기록한 "Docker 데몬 미실행으로 NOT_RUN" 제한은 해소됐다. 남은 미실행은 #9(실제 브라우저 키보드 조작)와 #2 의 브라우저 콘솔·네트워크 탭 확인이며, 둘 다 사람이 브라우저를 조작해야 한다.
- 이 호스트의 Docker Desktop 은 포트 80·443 을 호스트에 게시하지 못한다(dockerd 는 포트를 점유해 다른 컨테이너의 바인딩을 거부하지만 호스트 리스너가 생기지 않는다. 8080 은 정상 게시된다). 그래서 #10 의 HTTP·HTTPS 검사는 호스트가 아니라 compose 네트워크 안의 클라이언트 컨테이너에서 수행했다. nginx 동작 검증에는 영향이 없고, 8000 차단은 포트 접근이 아니라 `docker inspect` 의 `PortBindings={}` 로 확정했다.
- `frontend/nginx.conf` 의 `access_log /var/log/nginx/access.log` 는 베이스 이미지에서 `/dev/stdout` 심볼릭 링크라 컨테이너 stdout 으로 나간다(파일로 읽으면 블로킹된다). `ws-access.log` 는 컨테이너 안의 실제 파일이지만 볼륨이 없어 컨테이너 제거 시 사라진다. 운영에서 WebSocket 접근 로그를 보존하려면 별도 볼륨이나 로깅 드라이버가 필요하다.
- RELEASE-01 검증 중 `webterm:latest` 이미지가 존재하지 않아 새로 빌드했다. 이 이미지가 없으면 셸 기능은 동작하지 않으며 `main.py` startup 은 경고만 남기고 기동한다. 배포 환경에서도 이미지 존재를 별도로 보장해야 한다.
- RELEASE-01 #10 검증은 임시 override 로 실제 DB 마운트(`./data/linux_web_gui.db`)를 빈 임시 파일로 대체하고 certbot 서비스를 기동하지 않은 상태에서 수행했다. 실제 운영 프로필을 그대로 기동하면 backend 가 실 DB 에 마이그레이션과 스냅샷 기록을 수행하고 certbot 이 실제 도메인 대상 renew 를 시도하므로, 검증 목적의 기동에는 이 격리가 필요하다.
- **Windows 호스트에서는 셸(터미널) 기능이 동작하지 않는다.** `backend/routers/shell.py`가 POSIX 전용 모듈(`fcntl`·`termios`·`tty`)과 `os.setsid`를 사용하므로 Windows에서 import가 실패하고, `main.py`는 이를 `except ImportError`로 잡아 **경고 한 줄만 남기고 기동한다**(`⚠️ shell 라우터 등록 실패`). 그 결과 `/ws/shell`과 `/api/shell/*`가 아예 등록되지 않는다. `/api/auth/ws-tickets/shell`은 auth 라우터 소속이라 정상 등록되므로, 화면은 ticket 발급까지 성공한 뒤 연결 단계에서 실패한다. 대상 배포 환경(Linux/EC2/컨테이너)에서는 정상이며 도커 기동 시 이 경고가 없음을 확인했다. 다만 기능이 통째로 빠진 채 "정상 기동"으로 보이는 구조라, 운영에서 셸 부재를 조기에 알아채기 어렵다.
- `backend/cli/create_admin.py` 실행 시 passlib이 bcrypt 4.x의 버전 정보를 읽지 못해 `(trapped) error reading bcrypt version` 트레이스백을 출력한다. passlib이 내부적으로 처리하므로 해싱과 계정 생성은 정상 동작하지만(`Administrator created` 확인), 문서화된 운영 명령이 실패처럼 보이는 출력을 내는 문제가 남아 있다.
- RELEASE-01 브라우저 검증용으로 `backend/release01-dev.db`(합성 admin 1개)를 만들었다. `.gitignore`의 `*.db`에 걸려 추적되지 않는다. 재확인이 필요 없으면 삭제해도 무방하다.
- RELEASE-02 재평가 결과 `docs/re-evaluation.md`는 `.gitignore` 정책상 저장소에 포함되지 않는다(운영 문서 4개만 예외). 재평가 근거와 남은 위험 7건은 로컬에만 남으므로, 외부 공유가 필요하면 별도 결정이 필요하다.
- 계획 전체 완료 시점의 미해결 위험은 `docs/re-evaluation.md` §5에 우선순위로 정리했다. 이 중 1(로그아웃 토큰 무효화), 2(단일 프로세스 가정), 3(관측 가능성)은 다중 인스턴스·실사용자 환경으로 전제가 바뀌면 즉시 차단 사유가 된다.
- CI-FIX: PR #1 에서 GitHub Actions 가 처음 실제 실행되며 `docker compose config` 단계가 실패했다. 원인은 워크플로가 `SECRET_KEY`·`DATABASE_URL`·`DOMAIN_NAME` 을 제공하지 않은 것이다(compose 가 `${VAR:?}` 로 요구하는 SECRET-01 fail-closed 설계). `scripts/gate.sh` 는 합성값을 주입했으나 `.github/workflows/ci.yml` 에는 같은 처리가 없어, 로컬 게이트는 계속 통과하고 CI 만 실패하는 불일치가 있었다. CI 가 `NOT_RUN` 인 동안 드러나지 않았다. 워크플로에 게이트와 동일한 합성값을 주입하고 개발 프로필 검증도 추가했으며, 불일치 재발을 막는 `backend/tests/test_ci_workflow.py`(5건)를 추가했다. 이 검사는 CI 가 필수 변수를 제공하는지, 두 프로필을 모두 보는지, 그리고 **compose 의 요구 자체를 없애 통과시키지 않았는지**를 함께 확인한다.
- **DEPLOY-ENV: 배포 환경에서 도메인 발급이 불가하다.** 대상 EC2 인스턴스는 인프라 관리자에게 권한을 받아 사용하는 계정이며 고정 공인 IP만 할당받았다. Let's Encrypt 는 IP 에 인증서를 발급하지 않으므로 **운영 HTTPS 프로필은 "미검증"이 아니라 "실행 불가"** 이다(`docs/evaluation.md:600` 의 "검증하지 않았다"와 성격이 다르다). 실질적 배포 모드는 개발 override(`APP_ENV=development`)를 붙인 HTTP 프로필이며, 그 결과 **로그인 자격증명·JWT·WebSocket ticket 이 평문으로 전송된다.** 코드의 TLS 강제와 인증서 fail-closed 설계(`frontend/start.sh:18-21`)는 약화하지 않고 그대로 두었고, 이 환경에서 해당 경로를 쓰지 못할 뿐이다. 완화책은 인바운드 소스를 사용 IP `/32` 로 제한하는 것이다. 이 제약은 계획 문서 어디에도 기록되어 있지 않아 `docs/operations.md` §4.1 이 도메인 보유를 전제로 쓰여 있었고, 문서를 따라간 결과가 컨테이너 재시작 루프였다. `docs/operations.md`(§1·§3·§4·§7)와 `README.md`(빠른 시작·실행·보안·문제 해결)에 반영했다.
- DEPLOY-ENV 부수 제약: 보안 그룹 인바운드 규칙 변경 권한이 없어 포트 개방이 인프라 관리자 요청에 의존한다. 배포 절차에 외부 의존 단계가 하나 남는다.
- DEPLOY-ENV 함정 2건을 문서화했다. (1) 인증서 없이 운영 프로필을 띄우면 `restart: always` 때문에 무한 재시작하는데 `docker compose up -d` 는 성공한 것처럼 보인다. `docker compose ps` 확인이 필요하다. (2) `/health` 는 운영 설정에서도 80 번 포트에서 200 을 반환하므로(`frontend/nginx.conf:52-56`) 프로필 판별에 쓸 수 없다. `/` 로 확인해야 하며 301 이면 운영 프로필이다. 추가로 운영 프로필에 한 번 접속하면 브라우저가 `return 301` 영구 리디렉션을 캐시해, 개발 프로필로 전환한 뒤에도 접속이 실패한다(실제로 이 증상이 발생했고 캐시가 원인이었다).
- **AI-NARRATE-01 실제 구동 검증 중 실 AWS Bedrock 호출 1회가 발생했다(사전 고지 없이).** 이 sandbox에는 `aws` CLI도 `~/.aws/`도 없어 자격 증명이 없다고 판단했으나, boto3 기본 자격 증명 체인이 (아마도 인스턴스/컨테이너 role로) 실제 자격 증명을 찾아 `narrate()`가 `degraded:false`로 실제 응답(request_id·토큰 사용량 포함)을 반환했다. 응답을 확인한 즉시 추가 호출을 중단했고(인젝션 케이스 등 나머지 분기는 기존 mock 기반 focused 테스트로만 검증), 이 1회 호출은 매우 저렴한 단건 Converse 호출이지만 사용자 사전 승인 없이 발생한 실비용이라는 점을 명시적으로 기록한다.
- `toolConfig` 기반 구조화 출력은 이번에 추가한 `narrate()` 경로에만 적용했다. 기존 `chat`/`hint`가 쓰는 `tutor()`/`build_prompt()`(프롬프트 텍스트로 JSON 요청 + 코드펜스 정규식 파싱, `aws_ref.md:214`가 "최소 방어"라고 명시한 방식)는 이번 범위에서 바꾸지 않았다(AI-NARRATE-TOOLCONFIG 결정). 같은 신뢰성 문제가 `chat`/`hint`에도 남아 있으며, 이번 실 Bedrock 호출로 `toolConfig` 자체는 실제 API에서 정상 동작함을 확인했으니 후속 작업으로 `tutor()`도 옮기는 걸 검토할 수 있다.
- AI-NARRATE-01의 `narrate` rate limiter 호출은 `reject=False`(조용한 폴백, 429 미반환) 경로를 처음으로 실사용했다. 기존 `chat`/`hint`는 둘 다 `reject=True`(기본값)라 이 분기가 이전까지 죽은 코드였다.
- AI-NARRATE-01은 `docs/re-plan.md` 밖 범위라 Phase 진행 상태(Task Status 표의 Phase 0~9)에는 포함되지 않는다. `bash scripts/gate.sh`의 frontend lint 실패(위 Validation Log)는 이번 작업이 만든 게 아니라 이전부터 있던 `frontend/src/utils/terminalSafety.js`의 문제이며, 고치지 않고 그대로 남겨뒀다(요청과 무관한 정리 금지).
- **AI-NARRATE-01 `_UNMATCHED_INSTRUCTION` 가드레일 추가는 프롬프트 텍스트만 바꾼 것이다.** 실제 모델이 "does not exist"류 단정을 더 이상 하지 않는지는 mock 기반 단위 테스트(가드레일 문구가 프롬프트에 포함됐는지만 확인)로는 보장할 수 없고, 다음 실 Bedrock 호출(수동 UI 확인 또는 `test_bedrock_live.py` 계열) 때 육안으로 재확인이 필요하다. LLM 프롬프트 지시는 결정론적 보장이 아니라 확률적 완화라는 한계가 있다.
