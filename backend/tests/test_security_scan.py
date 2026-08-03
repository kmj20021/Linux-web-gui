"""Focused regression tests for the fail-closed source security scanner."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCANNER = REPOSITORY_ROOT / "scripts" / "security_scan.py"
SAFE_NGINX_CONFIG = """
log_format websocket '$remote_addr [$time_local] "$request_method $uri" $status';

server {
    location /ws/ {
        access_log /var/log/nginx/websocket_access.log websocket;
    }
}
""".lstrip()


def _write(root: Path, relative_path: str, source: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _make_safe_repository(root: Path) -> None:
    _write(root, "backend/main.py", '"""Safe fixture application."""\n')
    for relative_directory in (
        "backend/core",
        "backend/routers",
        "backend/cli",
        "frontend/src",
    ):
        (root / relative_directory).mkdir(parents=True, exist_ok=True)
    _write(root, "frontend/nginx.conf", SAFE_NGINX_CONFIG)
    _write(
        root,
        "docker-compose.yml",
        """
services:
  backend:
    environment:
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required}
""".lstrip(),
    )


def _run_scanner(
    *arguments: str,
    working_directory: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCANNER), *arguments],
        cwd=working_directory,
        capture_output=True,
        check=False,
        encoding="utf-8",
        timeout=30,
    )


@pytest.mark.parametrize(
    ("category", "relative_path", "source", "forbidden_fragments"),
    [
        pytest.param(
            "SECRET_ENV_FALLBACK",
            "backend/main.py",
            (
                "import os\n"
                'runtime_value = os.getenv("SECRET_KEY", '
                '"fixture-env-fallback-value")\n'
            ),
            ("fixture-env-fallback-value", "runtime_value = os.getenv"),
            id="secret-env-fallback",
        ),
        pytest.param(
            "HARDCODED_CREDENTIAL",
            "backend/main.py",
            'password = "fixture-hardcoded-credential-value"\n',
            ("fixture-hardcoded-credential-value", 'password = "'),
            id="hardcoded-credential",
        ),
        pytest.param(
            "SENSITIVE_PY_LOG",
            "backend/main.py",
            (
                "import logging\n"
                'logging.warning("https://fixture.invalid/ws?'
                'token=fixture-python-log-value")\n'
            ),
            ("fixture-python-log-value", "logging.warning"),
            id="sensitive-python-log",
        ),
        pytest.param(
            "SENSITIVE_JS_CONSOLE",
            "frontend/src/client.js",
            'console.log("Bearer fixture-javascript-log-value");\n',
            ("fixture-javascript-log-value", "console.log"),
            id="sensitive-javascript-console",
        ),
        pytest.param(
            "NGINX_REQUEST_LOG",
            "frontend/nginx.conf",
            (
                "# fixture-nginx-source-marker\n"
                "log_format websocket '$remote_addr $uri $request_uri';\n"
                "server {\n"
                "    location /ws/ {\n"
                "        access_log /var/log/nginx/access.log websocket;\n"
                "    }\n"
                "}\n"
            ),
            ("fixture-nginx-source-marker", "$request_uri"),
            id="unsafe-nginx-request-log",
        ),
        pytest.param(
            "SCAN_INPUT_ERROR",
            "backend/main.py",
            "def broken(\n# fixture-input-error-source-marker\n",
            ("fixture-input-error-source-marker", "def broken("),
            id="malformed-scan-input",
        ),
    ],
)
def test_scanner_reports_category_and_relative_path_without_source_disclosure(
    tmp_path: Path,
    category: str,
    relative_path: str,
    source: str,
    forbidden_fragments: tuple[str, ...],
) -> None:
    fixture_root = tmp_path / "fixture-repository"
    _make_safe_repository(fixture_root)
    _write(fixture_root, relative_path, source)

    result = _run_scanner("--root", str(fixture_root), working_directory=tmp_path)

    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        f"{category}: {relative_path}",
        "SECURITY_SCAN_FINDINGS: 1",
    ]
    assert result.stderr == ""
    combined_output = result.stdout + result.stderr
    if any(fragment in combined_output for fragment in forbidden_fragments):
        pytest.fail(
            "scanner output disclosed fixture values or source text",
            pytrace=False,
        )


def test_root_scan_allows_non_logging_urls_and_skips_excluded_trees(
    tmp_path: Path,
) -> None:
    fixture_root = tmp_path / "selected-repository"
    unrelated_working_directory = tmp_path / "unrelated-working-directory"
    unrelated_working_directory.mkdir()
    _make_safe_repository(fixture_root)

    _write(
        fixture_root,
        "backend/core/url_builder.py",
        """
def websocket_url(token):
    return f"wss://fixture.invalid/ws?token={token}"
""".lstrip(),
    )
    _write(
        fixture_root,
        "frontend/src/client.js",
        """
export const websocketUrl = (token) =>
  `wss://fixture.invalid/ws?token=${token}`;
fetch(websocketUrl(token));
""".lstrip(),
    )

    excluded_sources = {
        "backend/core/tests/test_credentials.py":
            'password = "excluded-core-tests-value"\n',
        "backend/routers/test/credentials.py":
            'password = "excluded-router-test-value"\n',
        "backend/cli/venv/credentials.py":
            'password = "excluded-venv-value"\n',
        "backend/cli/.venv/credentials.py":
            'password = "excluded-dot-venv-value"\n',
        "frontend/src/node_modules/package/leak.js":
            "console.log(token);\n",
        "frontend/src/tests/leak.jsx":
            "console.log(secret);\n",
        "frontend/src/test/leak.js":
            "console.log(password);\n",
        "docs/example.py":
            'password = "excluded-docs-value"\n',
    }
    for relative_path, source in excluded_sources.items():
        _write(fixture_root, relative_path, source)

    result = _run_scanner(
        "--root",
        str(fixture_root),
        working_directory=unrelated_working_directory,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["SECURITY_SCAN_FINDINGS: 0"]
    assert result.stderr == ""


def test_current_repository_scan_is_clean(tmp_path: Path) -> None:
    result = _run_scanner(working_directory=tmp_path)

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["SECURITY_SCAN_FINDINGS: 0"]
    assert result.stderr == ""
