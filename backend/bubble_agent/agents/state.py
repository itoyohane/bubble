from __future__ import annotations

from typing import Any, TypedDict


class ProjectGraphState(TypedDict, total=False):
    bubble_id: str
    bubble_name: str
    run_id: str
    thread_id: str
    raw_idea: str
    depth: str
    instruction: str | None
    depth_policy: dict[str, Any]
    known_facts: list[str]
    assumptions: list[str]
    constraints: list[str]
    clarifying_questions: list[dict[str, Any]]
    user_answers: dict[str, str]
    scope_confirmed: bool
    candidate_directions: list[dict[str, Any]]
    selected_direction: dict[str, Any]
    mvp: dict[str, Any]
    recommended_stack: list[str]
    plan: dict[str, Any]
    review: dict[str, Any]
    revision_count: int
    current_stage: str
    errors: list[str]
