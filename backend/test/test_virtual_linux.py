#!/usr/bin/env python3
"""Standalone deterministic virtual Linux engine contract test."""
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from services.virtual_linux import execute_command


def main() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "ai_learning_scenarios.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    steps = [step for scenario in fixture["scenarios"] for problem in scenario["problems"] for step in problem["steps"]]
    assert [step["step"] for step in steps] == list(range(1, 25))

    outputs_by_input = defaultdict(list)
    for step in steps:
        key = (json.dumps(step["state_before"], sort_keys=True), step["command"])
        outputs_by_input[key].append((step["step"], step["expected_result"]))
    conflicts = [values for values in outputs_by_input.values() if len({output for _, output in values}) > 1]
    assert conflicts == [], conflicts

    for step in steps:
        state = deepcopy(step["state_before"])
        result = execute_command(state, step["command"])
        assert result.result_code == "success", (step["step"], result)
        assert result.output == step["expected_result"], (step["step"], result.output)
        assert result.state_before == step["state_before"]
        assert result.state_after == step["state_after"], step["step"]
        assert state == step["state_before"], "caller state must not be mutated"
        assert execute_command(state, step["command"]) == result

    initial = {"services": {"nginx": {"active": False, "enabled": False}}}
    attacks = [
        "systemctl start nginx; id", "systemctl start nginx && id",
        "systemctl start nginx || id", "systemctl status nginx | cat",
        "echo $(id)", "echo `id`", "cat /etc/passwd > /tmp/x",
        "cat < /etc/passwd", "printf hacked\nid", "python -c pass",
    ]
    for command in attacks:
        result = execute_command(initial, command)
        assert result.result_code == "unsupported_syntax", command
        assert result.state_before == initial and result.state_after == initial
        assert initial == {"services": {"nginx": {"active": False, "enabled": False}}}

    started = execute_command(initial, "systemctl start nginx").state_after
    repeated = execute_command(started, "systemctl start nginx")
    assert repeated.result_code == "success" and repeated.state_after == started
    missing = execute_command(initial, "systemctl start missing-service")
    assert missing.result_code == "unsupported_syntax" and missing.state_after == initial

    common_state = {
        "files": {"/srv/app/config.ini": {}, "/etc/nginx/nginx.conf": {}},
        "services": {
            "ssh": {"active": False, "enabled": True},
            "nginx": {"active": True, "enabled": False},
        },
        "packages": {"nginx": "installed"},
        "users": {"deploy": {"exists": True}},
    }
    common_copy = deepcopy(common_state)
    ls_result = execute_command(common_state, "ls")
    assert ls_result.output == "etc\npackages\nservices\nsrv\nusers"
    assert ls_result.result_code == "success" and ls_result.state_before == ls_result.state_after
    assert common_state == common_copy and execute_command(common_state, "ls") == ls_result
    assert execute_command({}, "ls").output == "(empty simulated directory)"

    service_output = execute_command(common_state, "systemctl status")
    assert service_output.output == "nginx: active; disabled\nssh: inactive; enabled"
    assert service_output.state_before == service_output.state_after == common_state
    assert execute_command({}, "systemctl status").output == "(no simulated services registered)"
    assert execute_command(common_state, "systemctl status nginx").output == "active"

    headers = execute_command(common_state, "curl -I http://localhost")
    assert headers.output == (
        "HTTP/1.1 200 OK\nServer: nginx (simulation)\n"
        "Content-Type: text/html\nContent-Length: 0\n\n"
    )
    assert headers.result_code == "success" and headers.state_before == headers.state_after
    inactive = {"services": {"nginx": {"active": False, "enabled": False}}}
    refused = execute_command(inactive, "curl -I http://localhost")
    assert refused.output == "curl: (7) Failed to connect to localhost port 80: Connection refused (simulation)"
    assert refused.result_code == "success" and refused.state_before == refused.state_after == inactive
    assert execute_command({}, "curl -I http://localhost").result_code == "success"
    assert execute_command(inactive, "curl http://localhost").result_code == "unsupported_syntax"

    invalid_shapes = [
        "ls -la", "ls relative", "curl -L http://localhost",
        "curl -I http://example.com", "curl http://example.com",
        "systemctl", "systemctl start", "systemctl start nginx extra",
        "systemctl status nginx extra", "ss -K", "ss -tlnp extra", "ss --all",
    ]
    for command in invalid_shapes:
        invalid = execute_command(common_state, command)
        assert invalid.result_code == "unsupported_syntax", command
        assert invalid.state_before == invalid.state_after == common_state

    # Real-world listening-port checks use flags (`ss -tlnp`, `ss -lnt`, ...);
    # they must behave exactly like bare `ss`, not be rejected as unsupported.
    listening = {"listening_ports": [22]}
    bare = execute_command(listening, "ss")
    for flagged in ("ss -tlnp", "ss -lnt", "ss -tuln", "ss -a"):
        result = execute_command(listening, flagged)
        assert result.result_code == "success" and result.output == bare.output, flagged
        assert result.state_after == bare.state_after, flagged

    # An unknown path is not an error: the simulator invents a plausible
    # listing once, persists it (state_after), and returns the same listing
    # on every later call so the fixture never has to pre-declare every path.
    unknown = execute_command(common_state, "ls /not/in/state")
    assert unknown.result_code == "success"
    assert unknown.output and "/" not in unknown.output.split("\n")[0]
    assert unknown.state_before == common_state
    assert unknown.state_after["directories"]["/not/in/state"] == unknown.output.split("\n")
    assert common_state == common_copy, "caller state must not be mutated"
    assert execute_command(common_state, "ls /not/in/state") == unknown
    persisted = execute_command(unknown.state_after, "ls /not/in/state")
    assert persisted.output == unknown.output and persisted.state_before == persisted.state_after
    other_path = execute_command(common_state, "ls /also/unknown")
    assert other_path.output != unknown.output, "different paths should not collide by construction"

    for output in (ls_result.output, service_output.output, headers.output, refused.output, unknown.output):
        assert "\x1b" not in output and "\x07" not in output

    print("PASS: fixture 24, common outputs, determinism, unsupported syntax, immutable simulation")


if __name__ == "__main__":
    main()
