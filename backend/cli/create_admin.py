"""Interactive, one-time creation of the application's first administrator."""

import asyncio
import getpass
import hmac
import re
import sys
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.database import AsyncSessionLocal, close_db, init_db
from core.models import WebUser
from core.security import get_password_hash


_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


class AdminBootstrapError(Exception):
    """A safe, user-facing bootstrap failure with no credential details."""


def _validate_credentials(username: str, password: str) -> None:
    if not _USERNAME_PATTERN.fullmatch(username):
        raise AdminBootstrapError(
            "Username must be 3-20 letters, numbers, or underscores"
        )
    if len(password) < 8:
        raise AdminBootstrapError("Password must contain at least 8 characters")


def _read_password(prompt: str) -> str:
    if sys.stdin.isatty():
        return getpass.getpass(prompt)

    value = sys.stdin.readline()
    if value == "":
        raise EOFError
    return value.rstrip("\r\n")


async def create_initial_admin(username: str, password: str) -> None:
    """Create the first admin, rejecting existing admins and duplicate names."""
    _validate_credentials(username, password)

    async with AsyncSessionLocal() as session:
        existing_admin = await session.execute(
            select(WebUser.id).where(WebUser.role == "admin").limit(1)
        )
        if existing_admin.scalar_one_or_none() is not None:
            raise AdminBootstrapError("An administrator already exists")

        existing_username = await session.execute(
            select(WebUser.id).where(WebUser.username == username).limit(1)
        )
        if existing_username.scalar_one_or_none() is not None:
            raise AdminBootstrapError("The account name is already in use")

        session.add(
            WebUser(
                username=username,
                hashed_password=get_password_hash(password),
                role="admin",
                is_active=True,
                created_by=None,
            )
        )
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise AdminBootstrapError(
                "The administrator could not be created because it already exists"
            ) from exc


async def _bootstrap(username: str, password: str) -> None:
    try:
        await init_db()
        await create_initial_admin(username, password)
    except SQLAlchemyError as exc:
        raise AdminBootstrapError(
            "The administrator could not be created"
        ) from exc
    finally:
        await close_db()


def main(argv: Sequence[str] | None = None) -> int:
    """Read credentials interactively; command-line credential arguments are forbidden."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        print(
            "This command does not accept command-line arguments",
            file=sys.stderr,
        )
        return 2

    try:
        username = input("Administrator username: ").strip()
        password = _read_password("Administrator password: ")
        confirmation = _read_password("Confirm password: ")
    except (EOFError, KeyboardInterrupt):
        print("Administrator creation cancelled", file=sys.stderr)
        return 2

    if not hmac.compare_digest(password, confirmation):
        print("Passwords do not match", file=sys.stderr)
        return 2

    try:
        asyncio.run(_bootstrap(username, password))
    except AdminBootstrapError as exc:
        print(f"Administrator creation failed: {exc}", file=sys.stderr)
        return 1

    print("Administrator created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
