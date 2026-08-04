"""Read-only loader for the deterministic AI learning fixture."""
from __future__ import annotations

import json
import random
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "test" / "fixtures" / "ai_learning_scenarios.json"

# The final curriculum slot is a review round: one of the already-completed
# problems, re-served under this prefix so its history/progress tracking
# never collides with the original attempt at the same problem_id.
REVIEW_PREFIX = "review_"


@lru_cache(maxsize=1)
def load_curriculum() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _strip_review_prefix(task_key: str) -> str:
    return task_key[len(REVIEW_PREFIX):] if task_key.startswith(REVIEW_PREFIX) else task_key


def get_problem(scenario_key: str, task_key: str) -> dict | None:
    real_task_key = _strip_review_prefix(task_key)
    for scenario in load_curriculum()["scenarios"]:
        if scenario["scenario_id"] != scenario_key:
            continue
        for problem in scenario["problems"]:
            if problem["problem_id"] == real_task_key:
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


def _problem_info_entry(scenario_key: str, task_key: str, *, title: str, description: str,
                         learning_goal: str, difficulty: str, task_index: int,
                         total_tasks: int) -> dict[str, Any]:
    return {
        "scenario_id": scenario_key,
        "task_id": task_key,
        "title": title,
        "description": description,
        "learning_goal": learning_goal,
        "difficulty": difficulty,
        "total_tasks": total_tasks,
        "task_index": task_index,
    }


REVIEW_ROUND_LEARNING_GOAL = "지금까지 배운 내용을 종합적으로 복습한다."


def problem_info(scenario_key: str, task_key: str) -> dict[str, Any] | None:
    """Return the public, read-only metadata for one fixture problem or review round."""
    problems = list_problems()
    total_tasks = len(problems)
    if task_key.startswith(REVIEW_PREFIX):
        real_task_key = _strip_review_prefix(task_key)
        source = next(
            (p for p in problems
             if p["scenario_id"] == scenario_key and p["problem_id"] == real_task_key),
            None,
        )
        if source is None:
            return None
        return _problem_info_entry(scenario_key, task_key,
            title=f"복습: {source['title']}",
            description=source["grading"]["success"]["description"],
            learning_goal=REVIEW_ROUND_LEARNING_GOAL,
            difficulty="advanced", task_index=total_tasks, total_tasks=total_tasks)
    for task_index, problem in enumerate(problems, start=1):
        if problem["scenario_id"] != scenario_key or problem["problem_id"] != task_key:
            continue
        scenario = next(
            item for item in load_curriculum()["scenarios"] if item["scenario_id"] == scenario_key
        )
        return _problem_info_entry(scenario_key, task_key,
            title=problem["title"], description=problem["grading"]["success"]["description"],
            learning_goal=scenario["learning_goal"],
            difficulty=problem["difficulty"], task_index=task_index, total_tasks=total_tasks)
    return None


def curriculum_info() -> list[dict[str, Any]]:
    """Return public metadata for all problems in fixture order.

    The final slot previews the review round generically: the actual
    problem is only chosen once a session reaches it (see next_problem()).
    """
    problems = list_problems()
    total_tasks = len(problems)
    items = [
        problem_info(problem["scenario_id"], problem["problem_id"])
        for problem in problems[:-1]
    ]
    items.append(_problem_info_entry(
        "review", "review",
        title="복습 라운드",
        description="지금까지 푼 문제 중 하나를 무작위로 다시 풀어 복습합니다.",
        learning_goal=REVIEW_ROUND_LEARNING_GOAL,
        difficulty="advanced", task_index=total_tasks, total_tasks=total_tasks,
    ))
    return items


def difficulty_for_problem(scenario_key: str, task_key: str) -> str | None:
    if task_key.startswith(REVIEW_PREFIX):
        return "advanced" if get_problem(scenario_key, task_key) is not None else None
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


def _review_problem(source: dict[str, Any]) -> dict[str, Any]:
    review = deepcopy(source)
    review["problem_id"] = f"{REVIEW_PREFIX}{source['problem_id']}"
    review["title"] = f"복습: {source['title']}"
    review["difficulty"] = "advanced"
    return review


def next_problem(
    scenario_key: str, task_key: str, *, grade: str,
    session_seed: int | str | None = None,
) -> dict[str, Any] | None:
    """Advance only after success; otherwise keep the current problem.

    The final slot is a review round: a random pick among the problems
    already completed in this session, reusing their grading/initial_state
    under a ``review_``-prefixed id. ``session_seed`` (the session id) keeps
    repeated calls before the session actually advances consistent, while
    still varying the pick across different sessions.
    """
    problems = list_problems()

    if task_key.startswith(REVIEW_PREFIX):
        # The review round is always the final slot: stay on it until it
        # succeeds, then the curriculum is complete.
        if grade == "success":
            return None
        real_task_key = _strip_review_prefix(task_key)
        source = next(
            (p for p in problems
             if p["scenario_id"] == scenario_key and p["problem_id"] == real_task_key),
            None,
        )
        return _review_problem(source) if source else None

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
    next_index = current_index + 1
    if next_index >= len(problems):
        return None
    if next_index == len(problems) - 1:
        candidates = problems[:next_index]
        chosen = random.Random(session_seed).choice(candidates)
        return _review_problem(chosen)
    return deepcopy(problems[next_index])


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
