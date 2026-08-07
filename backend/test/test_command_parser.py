#!/usr/bin/env python3
"""Contract test for the shell-injection classifier used by AI narration."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.command_parser import looks_like_shell_injection, parse_command  # noqa: E402


def test_injection_patterns_are_flagged() -> None:
    for command in (
        "systemctl start nginx; id", "systemctl start nginx && id",
        "systemctl start nginx || id", "systemctl status nginx | cat",
        "echo $(id)", "echo `id`", "cat /etc/passwd > /tmp/x",
        "cat < /etc/passwd", "printf hacked\nid", "ss\rwhoami",
    ):
        assert looks_like_shell_injection(command), command
        assert parse_command(command).result_code == "unsupported_syntax"


def test_clean_but_unmatched_commands_are_not_flagged() -> None:
    for command in ("pwd", "whoami", "mkdir /tmp/x", "grep foo bar.txt", "history", "cd /tmp"):
        assert not looks_like_shell_injection(command), command
        assert parse_command(command).result_code == "unsupported_syntax"


def test_supported_commands_are_never_flagged() -> None:
    for command in ("ls", "systemctl status nginx", "ss -tlnp", "cat /srv/app/config.ini"):
        assert not looks_like_shell_injection(command), command


def main() -> None:
    test_injection_patterns_are_flagged()
    test_clean_but_unmatched_commands_are_not_flagged()
    test_supported_commands_are_never_flagged()
    print("PASS: shell-injection classifier matches parser rejection, unmatched clean commands unflagged")


if __name__ == "__main__":
    main()
