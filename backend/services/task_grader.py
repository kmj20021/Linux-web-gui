"""Deterministic, state-first grading for AI learning problems."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from services.command_parser import parse_command


@dataclass(frozen=True)
class GradeResult:
    grade: str
    description: str
    attempts: int
    hint_level: int
    next_hint_level: int | None
    matched_state: dict[str, Any]

    @property
    def completed(self) -> bool:
        return self.grade == "success"


def grade_problem(
    problem: Mapping[str, Any],
    state: Mapping[str, Any],
    command_history: Sequence[str] = (),
    *,
    previous_attempts: int = 0,
    hint_level: int = 0,
) -> GradeResult:
    """Grade a copied state using fixture rules in success/partial/failure order."""
    if previous_attempts < 0:
        raise ValueError("previous_attempts must be zero or greater")
    if hint_level not in {0, 1, 2, 3}:
        raise ValueError("hint_level must be between 0 and 3")

    state_copy = deepcopy(dict(state))
    history_copy = tuple(command_history)
    attempts = previous_attempts + 1
    grading = problem["grading"]

    for grade in ("success", "partial"):
        rule = grading[grade]
        matched = _match_rule(state_copy, rule, history_copy)
        if matched is not None:
            return _result(grade, rule, attempts, hint_level, matched)

    # A failure rule describes a known failure state. Unknown non-success states
    # are also failures, but keep an empty match record rather than invent facts.
    failure_rule = grading["failure"]
    matched = _match_rule(state_copy, failure_rule, history_copy) or {}
    return _result("failure", failure_rule, attempts, hint_level, matched)


def _result(
    grade: str,
    rule: Mapping[str, Any],
    attempts: int,
    hint_level: int,
    matched: dict[str, Any],
) -> GradeResult:
    suggested = None if grade == "success" else min(3, hint_level + 1)
    return GradeResult(
        grade=grade,
        description=str(rule["description"]),
        attempts=attempts,
        hint_level=hint_level,
        next_hint_level=suggested,
        matched_state=deepcopy(matched),
    )


def _match_rule(
    state: Mapping[str, Any], rule: Mapping[str, Any], command_history: Iterable[str]
) -> dict[str, Any] | None:
    matched: dict[str, Any] = {}
    required = rule.get("required_state")
    if required is not None:
        required_match = _match_required_state(state, required)
        if required_match is None:
            return None
        matched.update(required_match)

    any_required = rule.get("any_required_state")
    if any_required is not None:
        any_match = next(
            (
                match
                for candidate in any_required
                if (match := _match_required_state(state, candidate)) is not None
            ),
            None,
        )
        if any_match is None:
            return None
        matched.update(any_match)

    family = rule.get("observed_command_family")
    if family is not None:
        if not _observed_command_family(command_history, str(family)):
            return None
        matched["observed_command_family"] = family

    return matched


def _match_required_state(
    state: Mapping[str, Any], required: Mapping[str, Any]
) -> dict[str, Any] | None:
    matched: dict[str, Any] = {}
    for dotted_key, expected in required.items():
        found, actual = _resolve_dotted_key(state, dotted_key)
        # Entity absence is the fixture representation of ``exists: false``.
        if not found and dotted_key.endswith(".exists") and expected is False:
            found, actual = True, False
        if not found or actual != expected:
            return None
        matched[dotted_key] = deepcopy(actual)
    return matched


def _resolve_dotted_key(state: Mapping[str, Any], dotted_key: str) -> tuple[bool, Any]:
    """Resolve dotted paths while preserving dictionary keys containing dots."""
    current: Any = state
    remaining = dotted_key
    while remaining:
        if not isinstance(current, Mapping):
            return False, None
        if remaining in current:
            return True, current[remaining]

        segments = remaining.split(".")
        matched_key = None
        matched_length = 0
        for length in range(len(segments) - 1, 0, -1):
            candidate = ".".join(segments[:length])
            if candidate in current:
                matched_key = candidate
                matched_length = length
                break
        if matched_key is None:
            return False, None
        current = current[matched_key]
        remaining = ".".join(segments[matched_length:])
    return True, current


def _observed_command_family(command_history: Iterable[str], family: str) -> bool:
    """Observe only commands accepted by the Stage 4 allow-list parser."""
    for command_text in command_history:
        if not isinstance(command_text, str):
            continue
        parsed = parse_command(command_text)
        if parsed.command is not None and parsed.command.name == family:
            return True
    return False
