"""
마이그레이션: web_users.username, login_logs.username 컬럼을 login_id 로 RENAME

배경:
- SQLAlchemy 의 create_all() 은 기존 테이블에 컬럼을 추가/변경하지 않으므로,
  ORM 모델의 username -> login_id 리네임 후에도 기존 SQLite DB 파일은
  여전히 'username' 컬럼을 가지고 있어 앱이 동작하지 않는다.
- 본 스크립트는 기존 DB 파일의 컬럼명을 RENAME 하여 실데이터를 보존한다.

대상 컬럼:
- web_users.username  -> web_users.login_id
- login_logs.username -> login_logs.login_id
- web_users.created_by 는 이름을 변경하지 않는다 (값 의미만 'login_id' 로 동일).

사용법 (backend 디렉터리 기준):
    python migrations/rename_username_to_login_id.py [DB_PATH ...]

- 인자를 주지 않으면 기본으로 다음 두 경로를 모두 처리한다:
    ./linux_web_gui.db, ../data/linux_web_gui.db (존재하는 것만)
- 인자를 주면 지정한 경로만 처리한다.

특징:
- 멱등(idempotent): 이미 login_id 로 변경된 DB 는 건드리지 않고 스킵한다.
- SQLite 3.25.0+ 의 ALTER TABLE ... RENAME COLUMN 을 사용한다.
  (인덱스/UNIQUE 제약은 컬럼 리네임 시 SQLite 가 자동으로 따라간다.)
"""
import os
import sqlite3
import sys


# (테이블명, 기존컬럼, 신규컬럼)
RENAMES = [
    ("web_users", "username", "login_id"),
    ("login_logs", "username", "login_id"),
]


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def migrate_db(db_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"  [skip] 파일 없음: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    try:
        for table, old_col, new_col in RENAMES:
            cols = _column_names(conn, table)
            if not cols:
                print(f"  [skip] 테이블 없음: {table}")
                continue
            if new_col in cols:
                print(f"  [skip] {table}.{new_col} 이미 존재 (변경 불필요)")
                continue
            if old_col not in cols:
                print(f"  [skip] {table}.{old_col} 컬럼 없음")
                continue
            conn.execute(
                f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}"
            )
            print(f"  [ok]   {table}.{old_col} -> {table}.{new_col}")
        conn.commit()
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        targets = argv[1:]
    else:
        # 기본 대상: backend 디렉터리에서 실행한다고 가정
        targets = [
            os.path.join(".", "linux_web_gui.db"),
            os.path.join("..", "data", "linux_web_gui.db"),
        ]

    print("== username -> login_id 컬럼 리네임 마이그레이션 ==")
    for db_path in targets:
        print(f"- 대상 DB: {db_path}")
        migrate_db(db_path)
    print("== 완료 ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
