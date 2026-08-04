"""Read-only loader for the deterministic AI learning fixture."""
from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "test" / "fixtures" / "ai_learning_scenarios.json"


@lru_cache(maxsize=1)
def load_curriculum() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def get_problem(scenario_key: str, task_key: str) -> dict | None:
    for scenario in load_curriculum()["scenarios"]:
        if scenario["scenario_id"] != scenario_key:
            continue
        for problem in scenario["problems"]:
            if problem["problem_id"] == task_key:
                return deepcopy(problem)
    return None


def initial_state(scenario_key: str, task_key: str) -> dict | None:
    problem = get_problem(scenario_key, task_key)
    return deepcopy(problem["initial_state"]) if problem else None


DIFFICULTIES = ("beginner", "intermediate", "advanced")


def list_problems() -> list[dict[str, Any]]:
    """Return problems in the deterministic order declared by the fixture."""
    result: list[dict[str, Any]] = []
    for scenario_index, scenario in enumerate(load_curriculum()["scenarios"]):
        difficulty = DIFFICULTIES[min(scenario_index, len(DIFFICULTIES) - 1)]
        for problem in scenario["problems"]:
            item = deepcopy(problem)
            item["scenario_id"] = scenario["scenario_id"]
            item["difficulty"] = difficulty
            result.append(item)
    return result


def problem_info(scenario_key: str, task_key: str) -> dict[str, Any] | None:
    """Return the public, read-only metadata for one fixture problem."""
    problems = list_problems()
    total_tasks = len(problems)
    for task_index, problem in enumerate(problems, start=1):
        if problem["scenario_id"] != scenario_key or problem["problem_id"] != task_key:
            continue
        scenario = next(
            item
            for item in load_curriculum()["scenarios"]
            if item["scenario_id"] == scenario_key
        )
        return {
            "scenario_id": scenario_key,
            "task_id": task_key,
            "title": problem["title"],
            "description": problem["grading"]["success"]["description"],
            "learning_goal": scenario["learning_goal"],
            "difficulty": problem["difficulty"],
            "total_tasks": total_tasks,
            "task_index": task_index,
        }
    return None


def curriculum_info() -> list[dict[str, Any]]:
    """Return public metadata for all problems in fixture order."""
    return [
        problem_info(problem["scenario_id"], problem["problem_id"])
        for problem in list_problems()
    ]


def difficulty_for_problem(scenario_key: str, task_key: str) -> str | None:
    return next(
        (
            item["difficulty"]
            for item in list_problems()
            if item["scenario_id"] == scenario_key and item["problem_id"] == task_key
        ),
        None,
    )


def select_problem(completed_problem_ids: Iterable[str] = ()) -> dict[str, Any] | None:
    """Select the first unfinished problem; no random or model-driven choice."""
    completed = set(completed_problem_ids)
    return next(
        (deepcopy(problem) for problem in list_problems() if problem["problem_id"] not in completed),
        None,
    )


def next_problem(
    scenario_key: str, task_key: str, *, grade: str
) -> dict[str, Any] | None:
    """Advance only after success; otherwise keep the current problem."""
    problems = list_problems()
    current_index = next(
        (
            index
            for index, problem in enumerate(problems)
            if problem["scenario_id"] == scenario_key and problem["problem_id"] == task_key
        ),
        None,
    )
    if current_index is None:
        return None
    if grade != "success":
        return deepcopy(problems[current_index])
    if current_index + 1 >= len(problems):
        return None
    return deepcopy(problems[current_index + 1])


def hint_for_problem(
    scenario_key: str, task_key: str, level: int
) -> dict[str, Any] | None:
    if level not in {1, 2, 3}:
        raise ValueError("hint level must be between 1 and 3")
    problem = get_problem(scenario_key, task_key)
    if problem is None:
        return None
    return deepcopy(next(hint for hint in problem["hints"] if hint["level"] == level))


def progress_after_grade(
    scenario_key: str,
    task_key: str,
    *,
    grade: str,
    attempts: int,
    hint_level: int,
) -> dict[str, Any]:
    """Return explicit deterministic data needed by a later API/UI layer."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if hint_level not in {0, 1, 2, 3}:
        raise ValueError("hint_level must be between 0 and 3")
    current_difficulty = difficulty_for_problem(scenario_key, task_key)
    if current_difficulty is None:
        raise ValueError("unknown problem")
    following = next_problem(scenario_key, task_key, grade=grade)
    suggested_hint = None if grade == "success" else min(3, hint_level + 1)
    return {
        "attempts": attempts,
        "hint_level": hint_level,
        "next_hint_level": suggested_hint,
        "current_difficulty": current_difficulty,
        "next_scenario_id": following["scenario_id"] if following else None,
        "next_problem_id": following["problem_id"] if following else None,
        "next_difficulty": following["difficulty"] if following else None,
        "curriculum_completed": grade == "success" and following is None,
    }
