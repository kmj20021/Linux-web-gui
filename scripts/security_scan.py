#!/usr/bin/env python3
"""Fail-closed source scan for credential and sensitive logging regressions."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Iterable


PYTHON_ROOTS = (
    Path("backend/core"),
    Path("backend/routers"),
    Path("backend/cli"),
)
FRONTEND_ROOT = Path("frontend/src")
COMPOSE_PATH = Path("docker-compose.yml")
EXCLUDED_DIRECTORIES = {
    ".cache",
    ".venv",
    "__pycache__",
    "dist",
    "generated",
    "node_modules",
    "test",
    "tests",
    "venv",
}
LOGGING_METHODS = {
    "critical",
    "debug",
    "error",
    "exception",
    "info",
    "log",
    "warn",
    "warning",
}
HASHING_CALLS = {
    "bcrypt.hash",
    "bcrypt.hashpw",
    "get_password_hash",
    "hash_password",
    "pwd_context.hash",
}
SENSITIVE_IDENTIFIERS = {
    "jwt",
    "password",
    "query",
    "queryparams",
    "querystring",
    "requesturi",
    "requesturl",
    "secret",
    "secretkey",
    "token",
    "uri",
    "url",
}
SENSITIVE_LITERAL = re.compile(
    r"(?:https?|wss?)://\S+"
    r"|(?:[?&]|\b)(?:jwt|password|secret|token)="
    r"|\bBearer\s+\S+"
    r"|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    re.IGNORECASE,
)

Finding = tuple[str, str]


class ScannerArgumentParser(argparse.ArgumentParser):
    """Prevent argparse errors from echoing user-supplied input."""

    def error(self, message: str) -> None:
        del message
        raise ValueError("invalid scanner arguments")


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _is_credential_name(value: str) -> bool:
    return _normalize_identifier(value) in {
        "accesstoken",
        "adminpassword",
        "apikey",
        "defaultpassword",
        "jwtsecret",
        "password",
        "passwordhash",
        "plainpassword",
        "refreshtoken",
        "secret",
        "secretkey",
        "token",
    }


def _is_plaintext_literal(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(node.value)
    )


def _assignment_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(
            name
            for element in target.elts
            for name in _assignment_names(element)
        )
    return ()


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _expression_is_sensitive(node: ast.AST) -> bool:
    for child in ast.walk(node):
        identifier = None
        if isinstance(child, ast.Name):
            identifier = child.id
        elif isinstance(child, ast.Attribute):
            identifier = child.attr

        if identifier is not None:
            normalized = _normalize_identifier(identifier)
            if (
                normalized in SENSITIVE_IDENTIFIERS
                or normalized.endswith("password")
                or normalized.endswith("secret")
                or normalized.endswith("token")
                or normalized.endswith("query")
                or normalized.endswith("querystring")
                or normalized.endswith("url")
                or normalized.endswith("uri")
            ):
                return True

        if (
            isinstance(child, ast.Constant)
            and isinstance(child.value, str)
            and SENSITIVE_LITERAL.search(child.value)
        ):
            return True
    return False


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return "."


def _add(
    findings: set[Finding],
    category: str,
    root: Path,
    path: Path,
) -> None:
    findings.add((category, _relative_path(root, path)))


def _is_excluded(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(
        part.casefold() in EXCLUDED_DIRECTORIES
        for part in relative.parts[:-1]
    )


def _read_text(
    root: Path,
    path: Path,
    findings: set[Finding],
) -> str | None:
    if path.is_symlink():
        _add(findings, "SCAN_INPUT_ERROR", root, path)
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _add(findings, "SCAN_INPUT_ERROR", root, path)
        return None


def _scan_python(
    root: Path,
    path: Path,
    findings: set[Finding],
) -> None:
    source = _read_text(root, path, findings)
    if source is None:
        return
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        _add(findings, "SCAN_INPUT_ERROR", root, path)
        return

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: Iterable[ast.AST]
            if isinstance(node, ast.Assign):
                targets = node.targets
            else:
                targets = (node.target,)
            if _is_plaintext_literal(node.value) and any(
                _is_credential_name(name)
                for target in targets
                for name in _assignment_names(target)
            ):
                _add(findings, "HARDCODED_CREDENTIAL", root, path)

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and _is_credential_name(key.value)
                    and _is_plaintext_literal(value)
                ):
                    _add(findings, "HARDCODED_CREDENTIAL", root, path)

        if not isinstance(node, ast.Call):
            continue

        function_name = _call_name(node.func)
        if function_name in {"os.getenv", "os.environ.get"}:
            key = node.args[0] if node.args else next(
                (
                    keyword.value
                    for keyword in node.keywords
                    if keyword.arg in {"key", "name"}
                ),
                None,
            )
            has_default = len(node.args) > 1 or any(
                keyword.arg == "default" for keyword in node.keywords
            )
            if (
                isinstance(key, ast.Constant)
                and key.value == "SECRET_KEY"
                and has_default
            ):
                _add(findings, "SECRET_ENV_FALLBACK", root, path)

        if (
            function_name.casefold() in HASHING_CALLS
            and node.args
            and _is_plaintext_literal(node.args[0])
        ):
            _add(findings, "HARDCODED_CREDENTIAL", root, path)

        for keyword in node.keywords:
            if (
                keyword.arg
                and _is_credential_name(keyword.arg)
                and _is_plaintext_literal(keyword.value)
            ):
                _add(findings, "HARDCODED_CREDENTIAL", root, path)

        is_logging_call = (
            isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ) or (
            isinstance(node.func, ast.Attribute)
            and node.func.attr.casefold() in LOGGING_METHODS
        )
        if is_logging_call and any(
            _expression_is_sensitive(argument)
            for argument in (
                *node.args,
                *(keyword.value for keyword in node.keywords),
            )
        ):
            _add(findings, "SENSITIVE_PY_LOG", root, path)


def _mask_javascript(source: str) -> str:
    """Blank comments and string literals while preserving template expressions."""

    masked = list(source)
    length = len(source)

    def blank(start: int, end: int) -> None:
        for index in range(start, min(end, length)):
            if source[index] not in "\r\n":
                masked[index] = " "

    def scan_string(index: int, quote: str) -> int:
        start = index
        index += 1
        while index < length:
            if source[index] == "\\":
                index += 2
                continue
            index += 1
            if source[index - 1] == quote:
                break
        blank(start, index)
        return index

    def scan_template(index: int) -> int:
        blank(index, index + 1)
        index += 1
        literal_start = index
        while index < length:
            if source[index] == "\\":
                blank(literal_start, index + 2)
                index += 2
                literal_start = index
                continue
            if source[index] == "`":
                blank(literal_start, index + 1)
                return index + 1
            if source.startswith("${", index):
                blank(literal_start, index + 1)
                index = scan_code(index + 2, stop_at_brace=True)
                literal_start = index
                continue
            index += 1
        blank(literal_start, length)
        return length

    def scan_code(index: int, stop_at_brace: bool = False) -> int:
        while index < length:
            if stop_at_brace and source[index] == "}":
                return index + 1
            if source.startswith("//", index):
                end = source.find("\n", index + 2)
                end = length if end == -1 else end
                blank(index, end)
                index = end
                continue
            if source.startswith("/*", index):
                end = source.find("*/", index + 2)
                end = length if end == -1 else end + 2
                blank(index, end)
                index = end
                continue
            if source[index] in {"'", '"'}:
                index = scan_string(index, source[index])
                continue
            if source[index] == "`":
                index = scan_template(index)
                continue
            if source[index] == "{":
                index = scan_code(index + 1, stop_at_brace=True)
                continue
            index += 1
        return length

    scan_code(0)
    return "".join(masked)


def _scan_javascript(
    root: Path,
    path: Path,
    findings: set[Finding],
) -> None:
    source = _read_text(root, path, findings)
    if source is None:
        return

    masked = _mask_javascript(source)
    console_call = re.compile(
        r"\bconsole\s*\.\s*(?:log|info|warn|error|debug|trace)\s*\("
    )
    for match in console_call.finditer(masked):
        open_paren = match.end() - 1
        depth = 1
        cursor = open_paren + 1
        while cursor < len(masked) and depth:
            if masked[cursor] == "(":
                depth += 1
            elif masked[cursor] == ")":
                depth -= 1
            cursor += 1
        if depth:
            _add(findings, "SCAN_INPUT_ERROR", root, path)
            return

        expression = masked[open_paren + 1 : cursor - 1]
        raw_expression = source[open_paren + 1 : cursor - 1]
        identifiers = {
            _normalize_identifier(identifier)
            for identifier in re.findall(
                r"[A-Za-z_$][A-Za-z0-9_$]*",
                expression,
            )
        }
        has_sensitive_identifier = any(
            identifier in SENSITIVE_IDENTIFIERS
            or identifier.endswith("password")
            or identifier.endswith("secret")
            or identifier.endswith("token")
            or identifier.endswith("query")
            or identifier.endswith("querystring")
            or identifier.endswith("url")
            or identifier.endswith("uri")
            for identifier in identifiers
        )
        has_sensitive_event_property = re.search(
            r"\bevent\s*\.\s*(?:data|reason)\b",
            expression,
            re.IGNORECASE,
        )
        if (
            has_sensitive_identifier
            or has_sensitive_event_property
            or SENSITIVE_LITERAL.search(raw_expression)
        ):
            _add(findings, "SENSITIVE_JS_CONSOLE", root, path)


def _location_block(config: str, start: int) -> str | None:
    open_brace = config.find("{", start)
    if open_brace == -1:
        return None
    depth = 1
    cursor = open_brace + 1
    while cursor < len(config) and depth:
        if config[cursor] == "{":
            depth += 1
        elif config[cursor] == "}":
            depth -= 1
        cursor += 1
    return config[open_brace + 1 : cursor - 1] if depth == 0 else None


def _scan_nginx(
    root: Path,
    path: Path,
    findings: set[Finding],
) -> None:
    source = _read_text(root, path, findings)
    if source is None:
        return

    config = re.sub(r"(?m)#.*$", "", source)
    websocket_format = re.search(
        r"\blog_format\s+websocket\b(.*?);",
        config,
        re.DOTALL,
    )
    unsafe_variable = re.compile(
        r"(?<![A-Za-z0-9_])"
        r"\$(?:request|request_uri|args|query_string)"
        r"(?![A-Za-z0-9_])"
    )
    if (
        websocket_format is None
        or "$uri" not in websocket_format.group(1)
        or unsafe_variable.search(websocket_format.group(1))
    ):
        _add(findings, "NGINX_REQUEST_LOG", root, path)

    websocket_locations = list(
        re.finditer(r"\blocation\s+/ws/\s*\{", config)
    )
    if not websocket_locations:
        _add(findings, "NGINX_REQUEST_LOG", root, path)
        return
    for location in websocket_locations:
        block = _location_block(config, location.start())
        if block is None:
            _add(findings, "SCAN_INPUT_ERROR", root, path)
            continue
        if not re.search(
            r"\baccess_log\s+[^;]*\swebsocket\s*;",
            block,
        ):
            _add(findings, "NGINX_REQUEST_LOG", root, path)


def _scan_compose(
    root: Path,
    path: Path,
    findings: set[Finding],
) -> None:
    source = _read_text(root, path, findings)
    if source is None:
        return

    assignment = re.compile(
        r"(?m)^\s*(?:-\s*)?"
        r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)"
        r"\s*(?::|=)\s*(?P<value>[^#\r\n]*)"
    )
    environment_default = re.compile(
        r"^\$\{[A-Za-z_][A-Za-z0-9_]*(?P<operator>:-|-)"
        r"(?P<default>.*)\}$"
    )
    for match in assignment.finditer(source):
        key = match.group("key")
        value = match.group("value").strip().strip("\"'")
        default_match = environment_default.fullmatch(value)

        if key == "SECRET_KEY" and default_match is not None:
            _add(findings, "SECRET_ENV_FALLBACK", root, path)

        if not _is_credential_name(key) or not value:
            continue
        if default_match is not None:
            if default_match.group("default"):
                _add(findings, "HARDCODED_CREDENTIAL", root, path)
            continue
        if re.fullmatch(
            r"\$\{[A-Za-z_][A-Za-z0-9_]*(?::\?|\?)[^}]*\}",
            value,
        ) or re.fullmatch(
            r"\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*",
            value,
        ):
            continue
        _add(findings, "HARDCODED_CREDENTIAL", root, path)


def _recursive_files(
    root: Path,
    relative_root: Path,
    suffixes: set[str],
    findings: set[Finding],
) -> list[Path]:
    directory = root / relative_root
    if directory.is_symlink() or not directory.is_dir():
        _add(findings, "SCAN_INPUT_ERROR", root, directory)
        return []
    try:
        candidates = list(directory.rglob("*"))
    except OSError:
        _add(findings, "SCAN_INPUT_ERROR", root, directory)
        return []
    return sorted(
        path
        for path in candidates
        if path.suffix.casefold() in suffixes
        and not _is_excluded(root, path)
    )


def scan(root: Path) -> set[Finding]:
    findings: set[Finding] = set()

    main_path = root / "backend/main.py"
    _scan_python(root, main_path, findings)
    for python_root in PYTHON_ROOTS:
        for path in _recursive_files(
            root,
            python_root,
            {".py"},
            findings,
        ):
            _scan_python(root, path, findings)

    for path in _recursive_files(
        root,
        FRONTEND_ROOT,
        {".js", ".jsx"},
        findings,
    ):
        _scan_javascript(root, path, findings)

    frontend_directory = root / "frontend"
    if frontend_directory.is_symlink() or not frontend_directory.is_dir():
        _add(findings, "SCAN_INPUT_ERROR", root, frontend_directory)
    else:
        try:
            nginx_paths = sorted(frontend_directory.glob("nginx*.conf"))
        except OSError:
            nginx_paths = []
            _add(findings, "SCAN_INPUT_ERROR", root, frontend_directory)
        if not nginx_paths:
            _add(
                findings,
                "SCAN_INPUT_ERROR",
                root,
                frontend_directory / "nginx*.conf",
            )
        for path in nginx_paths:
            _scan_nginx(root, path, findings)

    _scan_compose(root, root / COMPOSE_PATH, findings)
    return findings


def _emit(findings: set[Finding]) -> None:
    for category, relative_path in sorted(findings):
        print(f"{category}: {relative_path}")
    print(f"SECURITY_SCAN_FINDINGS: {len(findings)}")


def _parse_root(argv: list[str] | None) -> Path:
    parser = ScannerArgumentParser(
        description="Scan production sources for credential leakage risks.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to the scanner's repository).",
    )
    return parser.parse_args(argv).root.resolve()


def main(argv: list[str] | None = None) -> int:
    try:
        root = _parse_root(argv)
    except (OSError, RuntimeError, ValueError):
        findings = {("SCAN_INPUT_ERROR", ".")}
        _emit(findings)
        return 2

    if not root.is_dir():
        findings = {("SCAN_INPUT_ERROR", ".")}
        _emit(findings)
        return 2

    findings = scan(root)
    _emit(findings)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
