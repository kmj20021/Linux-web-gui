"""Explicit opt-in smoke test for the approved Bedrock Converse profile."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    if os.getenv("RUN_BEDROCK_LIVE") != "1":
        print("SKIP: set RUN_BEDROCK_LIVE=1 to call the approved Bedrock profile")
        return

    from services.bedrock import BedrockService

    result = BedrockService().tutor(
        learner_level="beginner",
        problem={"problem_id": "live_smoke", "title": "Linux 서비스 상태 확인"},
        state_summary={"services": {"nginx": {"active": False}}},
        grade="partial",
        last_command="systemctl status nginx",
        user_input="다음에 확인할 개념을 짧게 설명해 주세요.",
    )
    assert not result.degraded, result.model_dump()
    assert result.response is not None
    print(
        "PASS: approved Bedrock profile returned validated JSON; "
        f"request_id={result.metadata.request_id} latency_ms={result.metadata.latency_ms}"
    )


if __name__ == "__main__":
    main()
