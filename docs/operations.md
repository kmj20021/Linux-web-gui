# 운영·로컬 개발 가이드

이 문서는 실제 실행 절차를 다룹니다. 기능 개요와 권한 행렬은 `README.md`,
DB 마이그레이션·복구는 `docs/db-operations.md`를 참고하세요.

이 문서의 모든 예시 값은 합성값입니다. 실제 도메인·키·계정을 여기에 적지 마세요.

---

## 1. 환경변수

| 변수 | 필수 | 설명 |
|---|---|---|
| `SECRET_KEY` | **필수** | JWT·ticket 서명 키. 미설정이거나 알려진 placeholder면 서버가 시작을 거부한다. |
| `DATABASE_URL` | **필수** | 예: `sqlite+aiosqlite:////app/linux_web_gui.db` (컨테이너 내부 절대경로) |
| `DOMAIN_NAME` | **필수** | Nginx 설정과 TLS 인증서 경로에 사용 |
| `ALGORITHM` | 선택 | 기본 `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 선택 | Compose에서 `1440`으로 설정됨 |
| `APP_ENV` | 선택 | `development`면 HTTP 허용. 미설정 시 `production` |

키 생성 예:

```bash
openssl rand -hex 32
```

`changeme`, `secret`, `placeholder`, `your-secret-key-here` 같은 값은 거부됩니다.
이는 실수로 기본값을 운영에 올리는 것을 막기 위한 의도된 동작입니다.

`.env`는 저장소에 커밋하지 않습니다.

---

## 2. 로컬 개발 (Docker 없이)

가장 빠른 개발 루프입니다. 웹 터미널 기능은 Docker가 필요하므로 이 모드에서는
동작하지 않습니다.

### 백엔드

```bash
cd backend
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="sqlite+aiosqlite:///./linux_web_gui.db"

python -m uvicorn main:app --reload --port 8000
```

시작 시 `alembic upgrade head`가 자동 실행됩니다. 마이그레이션이 실패하면 서버는
기동하지 않습니다(스키마 오류를 정상으로 숨기지 않음).

- API 문서: `http://localhost:8000/docs`
- 헬스 체크: `http://localhost:8000/api/health`

### 최초 관리자 생성

```bash
cd backend
python -m cli.create_admin
```

대화형으로만 입력받습니다. 명령행 인자로 자격증명을 넘기면 거부됩니다(셸 이력
노출 방지). 사용자명 3~20자 영숫자·밑줄, 비밀번호 8자 이상.

### 프론트엔드

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

- 접속: `http://localhost:5173`
- Vite dev 서버가 `/api`와 `/ws`(WebSocket 포함)를 `http://localhost:8000`으로
  프록시하므로 별도 CORS 설정이 필요 없습니다.

---

## 3. Docker 개발 프로필 (HTTP)

TLS 없이 전체 스택을 띄웁니다. **운영에 사용하지 마세요.**

```bash
docker build -f Dockerfile.webterm -t webterm:latest .

docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

- 개발 override는 `APP_ENV=development`를 설정해 Nginx가 HTTP 설정을 쓰게 합니다.
- 443 포트 매핑을 제거하고 80만 노출합니다.
- 개발 override도 기본 파일의 필수 환경변수 보간을 그대로 상속하므로 `.env`에
  `SECRET_KEY`·`DATABASE_URL`·`DOMAIN_NAME`이 모두 있어야 합니다.

접속: `http://localhost`

---

## 4. 운영 배포 (HTTPS)

### 4.1 사전 조건

- 공인 IP와 A 레코드가 연결된 도메인
- 80·443 인바운드 허용
- `.env`에 필수 환경변수 3종

### 4.2 웹터미널 이미지

```bash
docker build -f Dockerfile.webterm -t webterm:latest .
```

이미지가 없으면 터미널 세션 생성이 실패합니다.

### 4.3 TLS 인증서 발급 (최초 1회)

운영 프로필은 인증서가 없으면 **의도적으로 시작에 실패**합니다. 순서가 중요합니다.

```bash
# 1) 개발 프로필로 HTTP만 띄워 webroot 검증 경로를 연다
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d frontend

# 2) 인증서 발급
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN_NAME" \
  --agree-tos --no-eff-email -m <운영자 메일 주소>

# 3) 개발 프로필 종료 후 운영으로 재기동
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
docker compose up -d
```

발급된 인증서는 `letsencrypt` 볼륨에 저장되며, `certbot` 서비스가 12시간 주기로
자동 갱신합니다.

### 4.4 기동

```bash
docker compose up -d
docker compose ps
```

### 4.5 배포 후 확인

```bash
# 백엔드가 호스트에 직접 노출되지 않아야 한다 (연결 거부가 정상)
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8000/api/health || echo "차단됨 (정상)"

# 미인증 요청은 401 이어야 한다
curl -sS -o /dev/null -w '%{http_code}\n' https://<도메인>/api/monitor/cpu     # 401
curl -sS -o /dev/null -w '%{http_code}\n' https://<도메인>/api/monitor/processes # 401

# 로그에 JWT·ticket 원문이 없어야 한다 (0건이 정상)
docker compose logs backend  | grep -cE 'eyJ[A-Za-z0-9_-]{10,}|ticket=' || true
docker compose logs frontend | grep -cE 'eyJ[A-Za-z0-9_-]{10,}|token='  || true
```

---

## 5. 운영 작업

### 상태와 로그

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

로그를 외부에 공유할 때는 사용자명·IP·토큰이 포함되지 않았는지 먼저 확인하세요.

### 백업

실행 DB는 `data/linux_web_gui.db`이며 Git에 추적되지 않습니다.
백업·마이그레이션 리허설·복구 절차는 **`docs/db-operations.md`** 를 따르세요.
운영 DB에 직접 마이그레이션을 적용하기 전에 반드시 복사본으로 리허설합니다.

### 사용자 관리

- 최초 관리자만 CLI로 만들고, 이후 계정은 웹 UI(사용자 관리)에서 만듭니다.
- 모든 admin은 동일한 관리 범위를 가집니다(전역 관리자).
- **마지막 활성 admin은 강등·비활성화·삭제할 수 없습니다.** 동시 요청에도 최소
  한 명이 보존됩니다.

### 데이터 보존

원본 모니터링 스냅샷은 **7일** 후 자동 삭제됩니다(보존 job이 24시간 간격 실행).

---

## 6. 검증

변경 후에는 표준 게이트를 한 번 실행합니다.

```bash
bash scripts/gate.sh
```

backend pytest, frontend lint·test·build, 운영·개발 Compose 구성, 소스 보안 스캔,
공백 검사를 한 번에 수행합니다. 개별 명령은 `README.md`의 개발 명령 절을 보세요.

---

## 7. 알려진 운영 제한사항

계획·구현상 현재 남아 있는 제약입니다. 배포 전에 인지하고 있어야 합니다.

- **단일 프로세스 전제**: 마지막 활성 admin 보호와 셸 세션 한도(사용자당 1, 전체 5)는
  단일 백엔드 프로세스의 메모리·잠금 범위입니다. 다중 worker나 다중 인스턴스로
  확장하려면 공유 저장소나 DB 수준 직렬화가 추가로 필요합니다.
- **실제 구동 검증 미완**: TLS 기동, 권한 행렬 실호출, 셸 컨테이너 격리는 현재까지
  정적·모의 검증으로만 확인했습니다. 실제 Docker 데몬 기반 확인은 릴리스 검증
  (`RELEASE-01`)에서 1회 수행할 예정입니다.
- **CI**: GitHub Actions workflow는 있으나 push 권한 문제로 호스팅 CI 실행 이력이
  없습니다. 동등한 명령을 로컬에서 실행해 대체하고 있습니다.
- **번들 크기**: 프론트엔드 단일 chunk가 500 kB를 넘습니다(`recharts`, `@xterm/xterm`).
  기능에는 영향이 없으나 초기 로딩이 느릴 수 있습니다.
- **셸 이미지 의존**: `webterm:latest` 이미지를 미리 빌드해야 터미널이 동작합니다.
