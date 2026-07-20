from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class BubbleModel(Base):
    __tablename__ = "bubbles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_idea: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    runs: Mapped[list[AgentRunModel]] = relationship(
        back_populates="bubble", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[ArtifactModel]] = relationship(
        back_populates="bubble", cascade="all, delete-orphan"
    )
    messages: Mapped[list[MessageModel]] = relationship(
        back_populates="bubble", cascade="all, delete-orphan"
    )
    decisions: Mapped[list[DecisionModel]] = relationship(
        back_populates="bubble", cascade="all, delete-orphan"
    )


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    bubble_id: Mapped[str] = mapped_column(
        ForeignKey("bubbles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    current_node: Mapped[str | None] = mapped_column(String(80))
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(30), nullable=False, default="v1")
    instruction: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    interrupt_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    bubble: Mapped[BubbleModel] = relationship(back_populates="runs")
    events: Mapped[list[RunEventModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RunEventModel(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        Index("ix_run_events_run_id_id", "run_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    node: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[AgentRunModel] = relationship(back_populates="events")


class ArtifactModel(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("bubble_id", "artifact_type", "version", name="uq_artifact_version"),
        Index("ix_artifacts_bubble_type", "bubble_id", "artifact_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    bubble_id: Mapped[str] = mapped_column(
        ForeignKey("bubbles.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    bubble: Mapped[BubbleModel] = relationship(back_populates="artifacts")


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    bubble_id: Mapped[str] = mapped_column(
        ForeignKey("bubbles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    bubble: Mapped[BubbleModel] = relationship(back_populates="messages")


class DecisionModel(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    bubble_id: Mapped[str] = mapped_column(
        ForeignKey("bubbles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    bubble: Mapped[BubbleModel] = relationship(back_populates="decisions")
