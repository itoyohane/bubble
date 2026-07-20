from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from bubble_agent.domain.schemas import (
    ArtifactRead,
    BubbleCreate,
    BubbleRead,
    BubbleStatus,
    BubbleUpdate,
    RunEventRead,
    RunRead,
    RunStatus,
)
from bubble_agent.persistence.models import (
    AgentRunModel,
    ArtifactModel,
    BubbleModel,
    DecisionModel,
    MessageModel,
    RunEventModel,
)


class NotFoundError(LookupError):
    pass


class Repository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _session(self) -> Session:
        return self._session_factory()

    def create_bubble(self, payload: BubbleCreate) -> BubbleRead:
        with self._session() as session, session.begin():
            model = BubbleModel(
                name=payload.name,
                raw_idea=payload.raw_idea,
                depth=payload.depth.value,
                status=BubbleStatus.DRAFT.value,
            )
            session.add(model)
            session.flush()
            session.add(MessageModel(bubble_id=model.id, role="user", content=payload.raw_idea))
            return BubbleRead.model_validate(model)

    def list_bubbles(self) -> list[BubbleRead]:
        with self._session() as session:
            rows = session.scalars(
                select(BubbleModel).order_by(BubbleModel.updated_at.desc())
            ).all()
            return [BubbleRead.model_validate(row) for row in rows]

    def get_bubble(self, bubble_id: str) -> BubbleRead:
        with self._session() as session:
            model = session.get(BubbleModel, bubble_id)
            if model is None:
                raise NotFoundError(f"Bubble {bubble_id} does not exist")
            return BubbleRead.model_validate(model)

    def update_bubble(self, bubble_id: str, payload: BubbleUpdate) -> BubbleRead:
        with self._session() as session, session.begin():
            model = session.get(BubbleModel, bubble_id)
            if model is None:
                raise NotFoundError(f"Bubble {bubble_id} does not exist")
            if payload.name is not None:
                model.name = payload.name.strip()
            if payload.depth is not None:
                model.depth = payload.depth.value
            model.updated_at = datetime.now(UTC)
            session.flush()
            return BubbleRead.model_validate(model)

    def set_bubble_status(self, bubble_id: str, status: BubbleStatus) -> None:
        with self._session() as session, session.begin():
            model = session.get(BubbleModel, bubble_id)
            if model is None:
                raise NotFoundError(f"Bubble {bubble_id} does not exist")
            model.status = status.value
            model.updated_at = datetime.now(UTC)

    def delete_bubble(self, bubble_id: str) -> None:
        with self._session() as session, session.begin():
            model = session.get(BubbleModel, bubble_id)
            if model is None:
                raise NotFoundError(f"Bubble {bubble_id} does not exist")
            session.delete(model)

    def create_run(
        self,
        *,
        bubble_id: str,
        thread_id: str,
        provider: str,
        model_name: str,
        instruction: str | None,
    ) -> RunRead:
        with self._session() as session, session.begin():
            if session.get(BubbleModel, bubble_id) is None:
                raise NotFoundError(f"Bubble {bubble_id} does not exist")
            run = AgentRunModel(
                bubble_id=bubble_id,
                thread_id=thread_id,
                provider=provider,
                model_name=model_name,
                instruction=instruction,
                status=RunStatus.QUEUED.value,
                prompt_version="v1",
            )
            session.add(run)
            session.flush()
            return RunRead.model_validate(run)

    def get_run(self, run_id: str) -> RunRead:
        with self._session() as session:
            model = session.get(AgentRunModel, run_id)
            if model is None:
                raise NotFoundError(f"Run {run_id} does not exist")
            return RunRead.model_validate(model)

    def list_runs(self, bubble_id: str) -> list[RunRead]:
        with self._session() as session:
            rows = session.scalars(
                select(AgentRunModel)
                .where(AgentRunModel.bubble_id == bubble_id)
                .order_by(AgentRunModel.created_at.desc())
            ).all()
            return [RunRead.model_validate(row) for row in rows]

    def update_run(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        current_node: str | None = None,
        error: str | None = None,
        interrupt_payload: dict[str, Any] | None = None,
    ) -> RunRead:
        with self._session() as session, session.begin():
            model = session.get(AgentRunModel, run_id)
            if model is None:
                raise NotFoundError(f"Run {run_id} does not exist")
            now = datetime.now(UTC)
            if status is not None:
                model.status = status.value
                if status == RunStatus.RUNNING and model.started_at is None:
                    model.started_at = now
                if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
                    model.finished_at = now
            if current_node is not None:
                model.current_node = current_node
            model.error = error
            model.interrupt_payload = interrupt_payload
            session.flush()
            return RunRead.model_validate(model)

    def add_event(
        self,
        *,
        run_id: str,
        node: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> RunEventRead:
        with self._session() as session, session.begin():
            event = RunEventModel(
                run_id=run_id,
                node=node,
                event_type=event_type,
                payload=payload or {},
                duration_ms=duration_ms,
            )
            session.add(event)
            session.flush()
            return RunEventRead.model_validate(event)

    def list_events(self, run_id: str, after_id: int = 0) -> list[RunEventRead]:
        with self._session() as session:
            rows = session.scalars(
                select(RunEventModel)
                .where(RunEventModel.run_id == run_id, RunEventModel.id > after_id)
                .order_by(RunEventModel.id)
            ).all()
            return [RunEventRead.model_validate(row) for row in rows]

    def save_artifacts(
        self,
        *,
        bubble_id: str,
        run_id: str,
        artifacts: dict[str, tuple[dict[str, Any], str]],
    ) -> list[ArtifactRead]:
        saved: list[ArtifactRead] = []
        with self._session() as session, session.begin():
            for artifact_type, (schema_data, markdown) in artifacts.items():
                current_version = session.scalar(
                    select(func.max(ArtifactModel.version)).where(
                        ArtifactModel.bubble_id == bubble_id,
                        ArtifactModel.artifact_type == artifact_type,
                    )
                )
                model = ArtifactModel(
                    bubble_id=bubble_id,
                    run_id=run_id,
                    artifact_type=artifact_type,
                    schema_data=schema_data,
                    markdown=markdown,
                    version=(current_version or 0) + 1,
                )
                session.add(model)
                session.flush()
                saved.append(ArtifactRead.model_validate(model))
        return saved

    def list_latest_artifacts(self, bubble_id: str) -> list[ArtifactRead]:
        with self._session() as session:
            max_versions = (
                select(
                    ArtifactModel.artifact_type,
                    func.max(ArtifactModel.version).label("version"),
                )
                .where(ArtifactModel.bubble_id == bubble_id)
                .group_by(ArtifactModel.artifact_type)
                .subquery()
            )
            rows = session.scalars(
                select(ArtifactModel)
                .join(
                    max_versions,
                    (ArtifactModel.artifact_type == max_versions.c.artifact_type)
                    & (ArtifactModel.version == max_versions.c.version),
                )
                .where(ArtifactModel.bubble_id == bubble_id)
                .order_by(ArtifactModel.artifact_type)
            ).all()
            return [ArtifactRead.model_validate(row) for row in rows]

    def list_artifact_versions(self, bubble_id: str, artifact_type: str) -> list[ArtifactRead]:
        with self._session() as session:
            rows = session.scalars(
                select(ArtifactModel)
                .where(
                    ArtifactModel.bubble_id == bubble_id,
                    ArtifactModel.artifact_type == artifact_type,
                )
                .order_by(ArtifactModel.version.desc())
            ).all()
            return [ArtifactRead.model_validate(row) for row in rows]

    def save_decisions(
        self, bubble_id: str, answers: dict[str, str], *, confirmed: bool
    ) -> None:
        confirmed_at = datetime.now(UTC) if confirmed else None
        with self._session() as session, session.begin():
            for key, value in answers.items():
                session.add(
                    DecisionModel(
                        bubble_id=bubble_id,
                        key=key,
                        value={"answer": value},
                        source="user",
                        confirmed_at=confirmed_at,
                    )
                )
