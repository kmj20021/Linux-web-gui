# 학습 기록 (Interview Prep Log)

> Claude Code가 매 세션마다 이 파일을 갱신합니다. 직접 수정해도 됩니다.
> 이해도 단계: 🔴 L0 모름 · 🟠 L1 암기 · 🟡 L2 What설명 · 🟢 L3 Why설명 · 🔵 L4 면접통과

## 진척 요약
| 주제 | 핵심 파일 | 현재 이해도 | 마지막 업데이트 |
|------|-----------|-------------|-----------------|
| 전체 아키텍처 | - | 🔴 L0 | - |
| AWS 구성 (EC2/Lambda/API Gateway 등) | - | 🔴 L0 | - |
| JWT 인증 | core/security.py | 🔴 L0 | - |
| WebSocket | routers/websocket.py | 🔴 L0 | - |
| Docker 격리 | docker-compose.yml, Dockerfile.webterm | 🔴 L0 | - |
| Nginx/TLS 리버스 프록시 | frontend/nginx.conf | 🔵 L4 (TLS·인증서·보안헤더·rate limit·WebSocket프록시) / 🟢 L3 (리버스프록시) | 2026-07-02 |

## 주제별 상세

### Nginx/TLS 리버스 프록시 — 🟢 L3 (리버스프록시) / 🔵 L4 (TLS·인증서신뢰) (2026-07-02)
- ✅ 리버스 프록시(L3): `upstream api_backend`=목적지 이름표 / `location`=분류 규칙 구분 이해. nginx가 경로 보고 분류(정적 `/`는 직접 응답, `/api/`·`/ws/`만 backend:8000로 proxy_pass). "왜 앞단에 두나"에 이유 4개(TLS 종료·HTTP→HTTPS·rate limit·정적 직접 응답)를 자기 말로 댐.
- ✅ TLS·인증서 신뢰(L4 통과): "암호화(TLS 종료) ≠ 신뢰(CA/도메인)"를 완전히 분리 이해. 암호화는 nginx가 인증서+키로 수행, Let's Encrypt는 발급(신분증)만. self-signed로도 암호화는 되지만 브라우저가 UNTRUSTED 경고→`-k`로 검증 우회. 인증서는 특정 도메인에 발급되므로 IP 직접 접속 시 이름 불일치로 또 경고. `ssl_certificate` 경로의 `DOMAIN_NAME`은 start.sh가 sed 치환.
- ✅ 보안 헤더(개념4 완료): **핵심 관통 원리 = 헤더는 "서버가 브라우저에게 주는 지시서", 실제 집행은 브라우저가 함**(→약점: 클라이언트 협조 필요). X-Frame-Options DENY🔵L4(클릭재킹=투명 iframe로 진짜 페이지 덮고 클릭 유도, 피해자 필요), nosniff🟢L3(MIME 스니핑 차단→업로드 파일 재판단 억제로 저장형 XSS 방어, 실행은 피해자 브라우저에서), HSTS🟢L3(브라우저에 https 강제 기억 max-age 1년→SSL stripping/MITM 방어, 301과 달리 사전 전환, 약점=최초1회 TOFU→해결책 HSTS preload). X-XSS-Protection(레거시·요즘 브라우저 제거됨, CSP가 대체)·Referrer-Policy(cross-site 시 origin만 전송해 URL 민감정보 유출 최소화)는 참고 수준.
- ✅ Rate limiting(개념5 완료, 🔵 L4): `limit_req_zone $binary_remote_addr`=IP별 카운트(서버전체 합산이면 정상 사용자 억울하게 차단), `rate=10r/s`=100ms에 1개 누수버킷. 봇넷 분산DDoS는 IP별 제한으로 원리상 못 막음(개별 IP는 합법)→실무는 CloudFront/Shield 등 엣지·인프라 계층에서 방어(계층별 역할분담). `burst=20`=순간폭주 구제용 대기 20칸, `nodelay`=대기분 즉시처리+빠름, 단 20칸 소진 후 초과분은 지연이 아니라 **즉시 503 거절**(nodelay의 정체성). 정상 순간몰림은 허용·지속 공격/brute-force는 초당10개로 강제제한+나머지 문전박대.
- ✅ WebSocket 프록시(개념6 완료, 🔵 L4): 터미널=양방향·비동기·실시간(주기적 아님)→폴링 대비 낭비↓지연↓(폴링은 자주=낭비/드물게=지연 트레이드오프, WebSocket이 딜레마 제거). 핸드셰이크=평범한 HTTP로 시작→`Upgrade`헤더로 승급요청→서버 101 Switching Protocols→양방향 파이프로 변신. `proxy_set_header Upgrade/Connection`=프록시는 hop-by-hop 헤더를 기본적으로 버리므로 backend까지 명시적으로 재전달해야 함(없으면 backend가 101 안 함→핸드셰이크 실패). `proxy_http_version 1.1`=Upgrade는 HTTP/1.1 필요. `proxy_read_timeout 86400`=idle 시 기본 60초에 정상연결 끊김 방지(트레이드오프: 너무 길면 죽은연결 자원낭비→하트비트 ping/pong 병행). 스케일아웃: WebSocket은 stateful(연결이 특정 서버 고정, 셸 프로세스가 그 머신 메모리에)→2대로 늘리면 다른 서버로 가면 세션 없음→**sticky session(세션 affinity)** 필수, 서버 간 상태공유는 Redis Pub/Sub.
- 🔁 다음에 다시 볼 것: (nginx 6개념 완료) 백엔드 WebSocket 코드 routers/websocket.py, JWT(core/security.py), Docker 격리, 전체 아키텍처, AWS 구성.
- 🎉 nginx.conf 6개념(리버스프록시·TLS·인증서신뢰·보안헤더·rate limit·WebSocket) 전부 L3~L4 도달.
- 📚 필요한 배경지식: HSTS/클릭재킹/MIME 스니핑, rate limiting(leaky bucket, burst), WebSocket 핸드셰이크(HTTP Upgrade).
- 🔎 이번 세션 핵심 산출물: 배포 설정이 자소서 주장과 달랐던 문제를 `frontend/nginx.conf`로 일원화(중복 `nginx/nginx.conf` 삭제)해 "주장 = 배포 현실"로 정합. 커밋 593712e/2d98669, origin/main push 완료.

<!--
새 주제를 다룰 때마다 아래 형식으로 추가:

### 주제명  — (이해도) (날짜)
- ✅ 설명할 수 있었던 것:
- ❌ 막힌 것:
- 🔁 다음에 다시 볼 것:
- 📚 필요한 배경지식:
-->

## 세션 로그
<!-- - YYYY-MM-DD: 무엇을 했고 어디까지 갔는지 한 줄 -->
- 2026-07-02: nginx.conf 6개념 완주 — 개념4(보안헤더 5종)·개념5(rate limiting 🔵L4)·개념6(WebSocket 프록시 🔵L4) 완료. WebSocket은 핸드셰이크(Upgrade/101)·hop-by-hop 재전달·read_timeout·스케일아웃(sticky session) 꼬리질문까지 방어. nginx 파트 종료. 다음 세션: 백엔드 코드(routers/websocket.py, core/security.py JWT) or Docker 격리 or 전체 아키텍처.
- 2026-07-01: 자소서(넷맨-초안) 팩트체크 → 배포 nginx 설정이 주장(TLS·보안헤더·rate limit)과 불일치한 것 발견 → frontend/nginx.conf로 일원화 수정 → 로컬 Docker 검증 → EC2 배포 후 `curl -kI`로 보안 헤더 5종·200 OK 최종 확인. 결론: 자소서 수정 불필요. 다음엔 Nginx 설정의 "왜"를 자기 말로 설명하는 드릴 필요(현재 L2).
