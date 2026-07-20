from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any
from uuid import uuid4

from bubble_agent.agents.graph import (
    ProjectPlanningGraph,
    RunCancelled,
    extract_interrupt_payload,
)
from bubble_agent.agents.state import ProjectGraphState
from bubble_agent.config import Settings
from bubble_agent.domain.schemas import (
    BubbleStatus,
    RunCreate,
    RunRead,
    RunResume,
    RunStatus,
)
from bubble_agent.models.base import StructuredModel
from bubble_agent.persistence.repositories import Repository


class RunOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: Repository,
        model: StructuredModel,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._model = model
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bubble-run")
        self._futures: dict[str, Future[None]] = {}

    def create_and_start(self, bubble_id: str, payload: RunCreate) -> RunRead:
        bubble = self._repository.get_bubble(bubble_id)
        thread_id = str(uuid4())
        run = self._repository.create_run(
            bubble_id=bubble_id,
            thread_id=thread_id,
            provider=self._model.provider,
            model_name=self._model.model_name,
            instruction=payload.instruction,
        )
        state: ProjectGraphState = {
            "bubble_id": bubble.id,
            "bubble_name": bubble.name,
            "run_id": run.id,
            "thread_id": thread_id,
            "raw_idea": bubble.raw_idea,
            "depth": bubble.depth.value,
            "instruction": payload.instruction,
            "errors": [],
        }
        self._futures[run.id] = self._executor.submit(self._run_initial, run.id, state)
        return run

    def resume(self, run_id: str, payload: RunResume) -> RunRead:
        run = self._repository.get_run(run_id)
        if run.status != RunStatus.WAITING:
            raise ValueError(f"Run {run_id} is not waiting for input")
        if not payload.confirm_scope:
            self.cancel(run_id)
            return self._repository.get_run(run_id)
        self._repository.save_decisions(run.bubble_id, payload.answers, confirmed=True)
        self._repository.update_run(
            run_id,
            status=RunStatus.QUEUED,
            interrupt_payload=None,
        )
        resume_payload = {"answers": payload.answers, "confirm_scope": True}
        self._futures[run.id] = self._executor.submit(
            self._run_resume, run.id, run.thread_id, resume_payload
        )
        return self._repository.get_run(run_id)

    def cancel(self, run_id: str) -> RunRead:
        run = self._repository.update_run(run_id, status=RunStatus.CANCELLED)
        self._repository.set_bubble_status(run.bubble_id, BubbleStatus.CANCELLED)
        self._repository.add_event(
            run_id=run_id,
            node=run.current_node or "orchestrator",
            event_type="run_cancelled",
        )
        return run

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _graph(self) -> ProjectPlanningGraph:
        return ProjectPlanningGraph(
            repository=self._repository,
            model=self._model,
            checkpoint_path=self._settings.checkpoint_path,
        )

    def _run_initial(self, run_id: str, state: ProjectGraphState) -> None:
        self._run_graph(run_id, lambda: self._graph().invoke(state))

    def _run_resume(
        self, run_id: str, thread_id: str, resume_payload: dict[str, Any]
    ) -> None:
        self._run_graph(
            run_id,
            lambda: self._graph().resume(thread_id=thread_id, resume_payload=resume_payload),
        )

    def _run_graph(self, run_id: str, invoke: Callable[[], dict[str, object]]) -> None:
        run = self._repository.get_run(run_id)
        try:
            self._repository.update_run(run_id, status=RunStatus.RUNNING, error=None)
            self._repository.set_bubble_status(run.bubble_id, BubbleStatus.RUNNING)
            self._repository.add_event(
                run_id=run_id, node="orchestrator", event_type="run_started"
            )
            result = invoke()
            interrupt_payload = extract_interrupt_payload(result)
            if interrupt_payload is not None:
                self._repository.update_run(
                    run_id,
                    status=RunStatus.WAITING,
                    current_node="await_user_confirmation",
                    interrupt_payload=interrupt_payload,
                )
                self._repository.set_bubble_status(run.bubble_id, BubbleStatus.WAITING)
                self._repository.add_event(
                    run_id=run_id,
                    node="await_user_confirmation",
                    event_type="human_input_required",
                    payload=interrupt_payload,
                )
                return
            if self._repository.get_run(run_id).status == RunStatus.CANCELLED:
                return
            self._repository.update_run(run_id, status=RunStatus.COMPLETED)
            self._repository.set_bubble_status(run.bubble_id, BubbleStatus.READY)
            self._repository.add_event(
                run_id=run_id, node="orchestrator", event_type="run_completed"
            )
        except RunCancelled:
            self._repository.update_run(run_id, status=RunStatus.CANCELLED)
            self._repository.set_bubble_status(run.bubble_id, BubbleStatus.CANCELLED)
        except Exception as exc:
            self._repository.update_run(
                run_id,
                status=RunStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )
            self._repository.set_bubble_status(run.bubble_id, BubbleStatus.FAILED)
            self._repository.add_event(
                run_id=run_id,
                node="orchestrator",
                event_type="run_failed",
                payload={"message": str(exc), "error_type": type(exc).__name__},
            )
