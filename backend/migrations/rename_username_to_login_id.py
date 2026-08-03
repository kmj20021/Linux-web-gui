"""[DEPRECATED / NO-OP] username -> login_id 컬럼 리네임 마이그레이션.

DB-01 이후 이 프로젝트의 사용자 식별 컬럼은 DEC-01 에 따라 `username` 으로
고정됐다. 이 스크립트가 하던 username -> login_id 리네임은 현재 ORM 모델
(core/models.py)과 정반대이며, 실행하면 스키마가 깨진다.

따라서 이 스크립트는 명시적 no-op 으로 남겨 둔다. 과거 자동화나 문서가 이
경로를 호출하더라도 어떤 DB 도 변경하지 않는다. 실제 스키마 변경은 Alembic
(`alembic upgrade head`, 앱 시작 시 자동 적용; core/db_migrations.py 참고)으로만
수행한다.
"""
import sys

_DEPRECATION = (
    "[deprecated] rename_username_to_login_id 는 DEC-01(username 유지)에 따라 "
    "폐기됐습니다. 아무 작업도 수행하지 않습니다. "
    "스키마 변경은 'alembic upgrade head' 를 사용하세요."
)


def migrate_db(db_path: str) -> None:
    """폐기됨: 어떤 DB 도 변경하지 않는다."""
    print(_DEPRECATION)


def main(argv: list[str]) -> int:
    print(_DEPRECATION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
