"""Stage 5 deterministic curriculum and task-grader checks."""
from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.curriculum import (  # noqa: E402
    hint_for_problem,
    list_problems,
    next_problem,
    progress_after_grade,
    select_problem,
)
from services.task_grader import grade_problem  # noqa: E402
from services.virtual_linux import execute_command  # noqa: E402


def _execute(initial_state: dict, commands: list[str]) -> dict:
    state = deepcopy(initial_state)
    for command in commands:
        result = execute_command(state, command)
        assert result.result_code == "success", (command, result)
        state = result.state_after
    return state


def test_all_answer_examples() -> None:
    problems = list_problems()
    assert len(problems) == 6
    checked = 0
    for problem in problems:
        for example in problem["answer_examples"].values():
            initial = deepcopy(problem["initial_state"])
            history = deepcopy(example["commands"])
            state = _execute(initial, history)
            state_snapshot = deepcopy(state)
            problem_snapshot = deepcopy(problem)
            history_snapshot = deepcopy(history)
            result = grade_problem(problem, state, history)
            assert result.grade == example["expected_grade"], (
                problem["problem_id"],
                example,
                result,
                state,
            )
            assert result.attempts == 1
            assert state == state_snapshot
            assert problem == problem_snapshot
            assert history == history_snapshot
            checked += 1
    assert checked == 24


def test_state_first_alternative_success() -> None:
    problem = list_problems()[0]
    target_state = deepcopy(problem["initial_state"])
    target_state["services"]["nginx"]["active"] = True
    result = grade_problem(problem, target_state, ["systemctl status nginx"])
    assert result.grade == "success"


def test_required_any_and_dotted_keys() -> None:
    file_problem = list_problems()[3]
    partial_state = deepcopy(file_problem["initial_state"])
    partial_state["files"]["/srv/app/config.ini"]["owner"] = "deploy"
    assert grade_problem(file_problem, partial_state).grade == "partial"

    success_state = deepcopy(partial_state)
    success_state["files"]["/srv/app/config.ini"].update(group="deploy", mode="640")
    assert grade_problem(file_problem, success_state).grade == "success"

    firewall_problem = list_problems()[5]
    firewall_state = _execute(
        firewall_problem["initial_state"], ["ufw allow 22/tcp"]
    )
    assert grade_problem(firewall_problem, firewall_state).grade == "success"


def test_safe_command_family_observation() -> None:
    problem = list_problems()[2]
    state = deepcopy(problem["initial_state"])
    assert grade_problem(problem, state, ["useradd operator"]).grade == "partial"
    for unsafe in (
        "echo useradd operator",
        "useradd operator; useradd deploy",
        "useradd operator && useradd deploy",
        "useradd operator\nuseradd deploy",
        "$(useradd operator)",
    ):
        assert grade_problem(problem, state, [unsafe]).grade == "failure"


def test_hint_attempt_and_progress_policy() -> None:
    problem = list_problems()[0]
    state = deepcopy(problem["initial_state"])
    first = grade_problem(problem, state)
    assert (first.attempts, first.next_hint_level) == (1, 1)
    second = grade_problem(problem, state, previous_attempts=1, hint_level=1)
    assert (second.attempts, second.next_hint_level) == (2, 2)
    fourth = grade_problem(problem, state, previous_attempts=3, hint_level=2)
    assert (fourth.attempts, fourth.next_hint_level) == (4, 3)
    many_attempts = grade_problem(problem, state, previous_attempts=9, hint_level=0)
    assert (many_attempts.attempts, many_attempts.next_hint_level) == (10, 1)
    max_hint = grade_problem(problem, state, previous_attempts=10, hint_level=3)
    assert (max_hint.attempts, max_hint.next_hint_level) == (11, 3)

    hint = hint_for_problem("service_recovery", "service_recovery_01", 2)
    assert hint and hint["kind"] == "command_family"
    hint["text"] = "caller mutation"
    assert hint_for_problem("service_recovery", "service_recovery_01", 2)["text"] != hint["text"]

    current = next_problem(
        "service_recovery", "service_recovery_01", grade="failure"
    )
    assert current and current["problem_id"] == "service_recovery_01"
    following = next_problem(
        "service_recovery", "service_recovery_01", grade="success"
    )
    assert following and following["problem_id"] == "service_recovery_02"
    assert following["difficulty"] == "beginner"

    progress = progress_after_grade(
        "service_recovery",
        "service_recovery_02",
        grade="success",
        attempts=1,
        hint_level=0,
    )
    assert progress["next_problem_id"] == "account_permissions_01"
    assert progress["next_difficulty"] == "intermediate"
    assert progress["next_hint_level"] is None

    failed_progress = progress_after_grade(
        "service_recovery",
        "service_recovery_01",
        grade="failure",
        attempts=10,
        hint_level=0,
    )
    assert failed_progress["next_hint_level"] == 1


def test_complete_without_bedrock() -> None:
    completed: list[str] = []
    expected_order = [problem["problem_id"] for problem in list_problems()]
    while problem := select_problem(completed):
        correct = problem["answer_examples"]["correct"]
        state = _execute(problem["initial_state"], correct["commands"])
        result = grade_problem(problem, state, correct["commands"])
        assert result.grade == "success"
        completed.append(problem["problem_id"])
    assert completed == expected_order
    assert select_problem(completed) is None


def main() -> None:
    test_all_answer_examples()
    test_state_first_alternative_success()
    test_required_any_and_dotted_keys()
    test_safe_command_family_observation()
    test_hint_attempt_and_progress_policy()
    test_complete_without_bedrock()
    print("PASS: 6 problems, 24 answer examples, grading, hints, deterministic progress")


if __name__ == "__main__":
    main()
