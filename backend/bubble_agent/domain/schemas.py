from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Depth(StrEnum):
    SPARK = "spark"
    BUILDER = "builder"
    ARCHITECT = "architect"


class BubbleStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    WAITING = "waiting"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BubbleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    raw_idea: str = Field(min_length=10, max_length=5000)
    depth: Depth = Depth.BUILDER

    @field_validator("name", "raw_idea")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class BubbleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    depth: Depth | None = None


class BubbleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    raw_idea: str
    depth: Depth
    status: BubbleStatus
    created_at: datetime
    updated_at: datetime


class ClarifyingQuestion(BaseModel):
    id: str
    question: str
    why_it_matters: str
    suggested_answer: str | None = None


class ClarificationResult(BaseModel):
    known_facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    questions: list[ClarifyingQuestion] = Field(default_factory=list)


class Direction(BaseModel):
    name: str
    summary: str
    value_score: int = Field(ge=1, le=5)
    effort_score: int = Field(ge=1, le=5)
    risk_score: int = Field(ge=1, le=5)
    rationale: str


class DirectionOptions(BaseModel):
    directions: list[Direction] = Field(min_length=1, max_length=3)


class DirectionSelection(BaseModel):
    selected_name: str
    rationale: str


class ProjectSummary(BaseModel):
    name: str
    one_liner: str
    problem: str
    target_users: list[str] = Field(min_length=1)
    goals: list[str] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)


class MvpPlan(BaseModel):
    objective: str
    must_have: list[str] = Field(min_length=1, max_length=8)
    nice_to_have: list[str] = Field(default_factory=list, max_length=6)
    out_of_scope: list[str] = Field(min_length=1)
    success_metrics: list[str] = Field(min_length=1)


class UserStory(BaseModel):
    role: str
    want: str
    benefit: str
    acceptance_criteria: list[str] = Field(min_length=1)


class StackChoice(BaseModel):
    layer: str
    technology: str
    rationale: str
    alternative: str | None = None


class ApiDraft(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    purpose: str


class DataEntity(BaseModel):
    name: str
    purpose: str
    key_fields: list[str]


class ProjectPlan(BaseModel):
    summary: ProjectSummary
    mvp: MvpPlan
    user_stories: list[UserStory] = Field(default_factory=list)
    tech_stack: list[StackChoice] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    data_entities: list[DataEntity] = Field(default_factory=list)
    api_draft: list[ApiDraft] = Field(default_factory=list)
    test_strategy: list[str] = Field(default_factory=list)


class ReviewIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    path: str
    problem: str
    recommendation: str


class ReviewResult(BaseModel):
    passed: bool
    issues: list[ReviewIssue] = Field(default_factory=list)


class RunCreate(BaseModel):
    instruction: str | None = Field(default=None, max_length=2000)


class RunResume(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    confirm_scope: bool = True


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bubble_id: str
    thread_id: str
    status: RunStatus
    current_node: str | None
    provider: str
    model_name: str
    prompt_version: str
    error: str | None
    interrupt_payload: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class RunEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    node: str
    event_type: str
    payload: dict[str, Any]
    duration_ms: int | None
    created_at: datetime


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bubble_id: str
    artifact_type: str
    schema_data: dict[str, Any]
    markdown: str
    version: int
    created_at: datetime


class ModelTestRequest(BaseModel):
    provider: str = "demo"
    model_name: str = "bubble-demo-v1"
    base_url: str | None = None
    api_key: str | None = None


class ModelTestResponse(BaseModel):
    ok: bool
    provider: str
    model_name: str
    latency_ms: int
    message: str
