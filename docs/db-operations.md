# DB 운영 절차 (DB-01)

이 문서는 스키마 버전 관리(Alembic) 도입 이후의 마이그레이션·백업·복구 절차를
정리한다. 실제 운영 DB(`data/linux_web_gui.db`)를 대상으로 하는 작업은 반드시
**백업 → 검증 → 적용** 순서로 수행하고, 파괴적 작업은 사용자 승인 후에만 한다.

## 스키마 버전 관리 개요

- 스키마의 단일 기준은 `backend/migrations/versions/` 의 Alembic 리비전이다.
- 앱 시작 시 `main.py` 의 startup 이벤트가 `core/db_migrations.run_migrations()` 로
  `alembic upgrade head` 를 실행한다. 실패하면 서버는 정상으로 위장하지 않고
  **시작에 실패한다(fail-closed)**.
- 과거의 임의 `ALTER TABLE`(`ensure_web_users_columns`)과 현재 모델과 반대인
  `migrations/rename_username_to_login_id.py` 리네임은 제거·폐기(no-op)됐다.
- 최초 리비전 `0001` 은 멱등적이다: 이미 테이블이 있는 기존 DB(alembic_version
  없음)에도 안전하게 적용되며, `web_users.created_by` 가 없으면 추가한다.

## 마이그레이션 실행

컨테이너 밖에서 수동으로 실행할 때(backend 디렉터리 기준):

```
# 현재 리비전 확인
DATABASE_URL="sqlite+aiosqlite:///./data/linux_web_gui.db" alembic current

# head 까지 업그레이드
DATABASE_URL="sqlite+aiosqlite:///./data/linux_web_gui.db" alembic upgrade head
```

`DATABASE_URL` 을 생략하면 `sqlite+aiosqlite:///./linux_web_gui.db` 기본값을 쓴다.
Alembic 은 비동기 드라이버(`+aiosqlite`)를 동기 드라이버로 변환해 실행한다.

## 백업 (변경 전 필수)

SQLite 파일 DB 이므로 파일 복사가 곧 백업이다. 운영 중이라면 SQLite 의 온라인
백업을 사용해 일관성을 보장한다.

```
# 1) 안전한 파일 복사 (서버 중지 시)
cp data/linux_web_gui.db data/linux_web_gui.db.bak.$(date +%Y%m%d%H%M%S)

# 2) 운영 중 온라인 백업 (권장)
sqlite3 data/linux_web_gui.db ".backup 'data/linux_web_gui.db.bak'"
```

백업 파일 경로와 시각을 기록하고, 백업이 없으면 마이그레이션을 진행하지 않는다.

## 검증 (복사본에서 리허설)

운영 DB 를 직접 바꾸기 전에 **복사본**에서 업그레이드를 리허설한다.

```
cp data/linux_web_gui.db /tmp/rehearsal.db
DATABASE_URL="sqlite+aiosqlite:////tmp/rehearsal.db" alembic upgrade head
# 스키마/데이터 확인 후 문제가 없으면 운영 DB 에 적용
```

빈 DB·기존 DB 복사본·이미 최신 DB 에 대한 자동 검증은
`backend/tests/test_db_migrations.py` 가 임시 DB 로 수행한다(실제 DB 미접근).

## 복구 (롤백)

마이그레이션 후 문제가 생기면 백업으로 되돌린다.

```
# 서버 중지 후
mv data/linux_web_gui.db data/linux_web_gui.db.failed
cp data/linux_web_gui.db.bak data/linux_web_gui.db
```

리비전 단위 되돌리기가 필요하면 백업 복원 후 아래를 쓴다(현재는 단일 리비전이라
사실상 스키마 제거이므로 데이터 손실에 주의).

```
DATABASE_URL="sqlite+aiosqlite:///./data/linux_web_gui.db" alembic downgrade -1
```

## 주의

- 실제 운영 DB 의 레코드·사용자명·IP·비밀·토큰은 로그·문서에 남기지 않는다.
- 저장소 추적 DB 제거(REPO-01)는 이 문서 범위 밖이며 별도 승인·백업 하에 한다.
