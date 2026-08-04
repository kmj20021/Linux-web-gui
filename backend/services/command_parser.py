"""Strict parser for commands supported by the virtual Linux simulator."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    action: str | None = None
    arguments: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParseResult:
    result_code: str
    command: ParsedCommand | None = None


_SHELL_SYNTAX = re.compile(r"(?:\r|\n|;|&&|\|\||\||`|\$\(|>>|2>|[<>])")
# Real `ss` listening-port checks always look like `-tlnp`/`-lnt`/etc: a single
# leading dash followed by short option letters. Anything else is rejected.
_SS_FLAGS = re.compile(r"-[tulnpaxw46]+")
_ACTIONS = {
    "systemctl": {"status", "start", "stop", "restart", "enable", "disable"},
    "ufw": {"allow", "deny", "status"},
    "apt": {"install", "remove"},
}
_SIMPLE = {"useradd", "userdel", "usermod", "passwd", "chmod", "chown", "ls", "cat", "ss", "curl", "ping"}


def parse_command(command_text: str) -> ParseResult:
    """Parse one allow-listed command without invoking a shell."""
    if not isinstance(command_text, str) or not command_text.strip():
        return ParseResult("unsupported_syntax")
    if _SHELL_SYNTAX.search(command_text):
        return ParseResult("unsupported_syntax")

    try:
        tokens = shlex.split(command_text, posix=True)
    except ValueError:
        return ParseResult("unsupported_syntax")
    if not tokens:
        return ParseResult("unsupported_syntax")

    name = tokens[0]
    if name in _ACTIONS:
        if len(tokens) < 2 or tokens[1] not in _ACTIONS[name]:
            return ParseResult("unsupported_syntax")
        action, arguments = tokens[1], tuple(tokens[2:])
        if name == "systemctl":
            valid = (action == "status" and len(arguments) in {0, 1}) or (
                action != "status" and len(arguments) == 1)
            if not valid:
                return ParseResult("unsupported_syntax")
        return ParseResult("success", ParsedCommand(name, action, arguments))
    if name in _SIMPLE:
        arguments = tuple(tokens[1:])
        if name == "curl" and arguments not in {
            ("http://localhost",), ("-I", "http://localhost")
        }:
            return ParseResult("unsupported_syntax")
        if name == "ls" and not (
            len(arguments) == 0 or
            (len(arguments) == 1 and arguments[0].startswith("/") and not arguments[0].startswith("/-"))
        ):
            return ParseResult("unsupported_syntax")
        if name == "ss" and arguments and not (
            len(arguments) == 1 and _SS_FLAGS.fullmatch(arguments[0])
        ):
            return ParseResult("unsupported_syntax")
        return ParseResult("success", ParsedCommand(name, arguments=arguments))
    return ParseResult("unsupported_syntax")
