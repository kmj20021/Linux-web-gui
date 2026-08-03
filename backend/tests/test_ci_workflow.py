"""CI 워크플로가 로컬 게이트와 어긋나지 않는지 검사한다.

`docker compose config` 는 `SECRET_KEY`·`DATABASE_URL`·`DOMAIN_NAME` 이 없으면
보간에 실패한다(SECRET-01 의 fail-closed 설계). `scripts/gate.sh` 는 합성값을
주입하지만 `.github/workflows/ci.yml` 은 그러지 않아, 로컬 게이트는 계속 통과하고
CI 만 실패했다. CI 가 한 번도 실행되지 않는 동안 이 불일치가 드러나지 않았다.

이 검사는 그 격차를 고정한다. 워크플로를 실제로 실행하지는 않지만, 게이트가
검증하는 명령을 CI 도 같은 전제로 실행하는지 정적으로 확인한다.
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GATE = REPO_ROOT / "scripts" / "gate.sh"

# docker-compose.yml 이 `${VAR:?...}` 로 요구하는 변수들.
REQUIRED_COMPOSE_VARS = ("SECRET_KEY", "DATABASE_URL", "DOMAIN_NAME")


@pytest.fixture(scope="module")
def workflow_text() -> str:
    if not WORKFLOW.exists():
        pytest.skip("CI 워크플로가 없는 환경이다")
    return WORKFLOW.read_text(encoding="utf-8")


def test_compose_step_supplies_every_required_variable(workflow_text):
    """compose 검증 단계가 필수 환경변수를 모두 제공해야 한다."""
    assert "docker compose config" in workflow_text, (
        "CI 가 Compose 구성 검증을 더 이상 하지 않는다"
    )
    for name in REQUIRED_COMPOSE_VARS:
        assert f"{name}:" in workflow_text, (
            f"CI 의 compose 검증 단계에 {name} 이 없다. "
            f"docker-compose.yml 이 이 값을 필수로 요구하므로 보간에 실패한다"
        )


def test_ci_validates_both_compose_profiles(workflow_text):
    """게이트와 같이 운영·개발 두 프로필을 모두 검증해야 한다."""
    assert "docker-compose.dev.yml" in workflow_text, (
        "CI 가 개발 프로필(docker-compose.dev.yml)을 검증하지 않는다. "
        "scripts/gate.sh 는 두 프로필을 모두 본다"
    )


def test_ci_does_not_weaken_the_compose_requirement():
    """합성값을 넣는 것으로 끝내고, 요구 자체를 없애지 않았는지 확인한다."""
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for name in REQUIRED_COMPOSE_VARS:
        assert f"${{{name}:?" in compose, (
            f"docker-compose.yml 이 {name} 을 더 이상 필수로 요구하지 않는다. "
            f"CI 를 통과시키려고 fail-closed 설계를 약화하면 안 된다"
        )


def test_ci_runs_the_same_checks_as_the_gate(workflow_text):
    """게이트의 핵심 검사가 CI 에서도 실행되는지 확인한다."""
    for command in (
        "pytest backend/tests",
        "run lint",
        "test -- --run",
        "run build",
        "scripts/security_scan.py",
    ):
        assert command in workflow_text, f"CI 에 `{command}` 단계가 없다"


def test_gate_still_injects_synthetic_compose_values():
    """게이트 쪽 주입이 사라지면 이번 불일치가 반대 방향으로 재발한다."""
    if not GATE.exists():
        pytest.skip("게이트 실행기가 없는 환경이다")
    gate = GATE.read_text(encoding="utf-8")
    for name in REQUIRED_COMPOSE_VARS:
        assert f'export {name}="${{{name}:-' in gate, (
            f"scripts/gate.sh 가 {name} 합성값을 더 이상 주입하지 않는다"
        )
