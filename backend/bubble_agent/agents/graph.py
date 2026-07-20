from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from bubble_agent.agents.policies import policy_for
from bubble_agent.agents.state import ProjectGraphState
from bubble_agent.artifacts.renderers import render_artifacts
from bubble_agent.domain.schemas import (
    ClarificationResult,
    DirectionOptions,
    DirectionSelection,
    MvpPlan,
    ProjectPlan,
    ReviewResult,
    RunStatus,
)
from bubble_agent.models.base import ModelGatewayError, SchemaT, StructuredModel
from bubble_agent.persistence.repositories import Repository

NodeResult = dict[str, Any]
NodeAction = Callable[[], NodeResult]


class RunCancelled(RuntimeError):
    pass


class ProjectPlanningGraph:
    """Depth-aware LangGraph workflow with durable SQLite checkpoints."""

    def __init__(
        self,
        *,
        repository: Repository,
        model: StructuredModel,
        checkpoint_path: Path,
    ) -> None:
        self._repository = repository
        self._model = model
        self._checkpoint_path = checkpoint_path

    def invoke(self, state: ProjectGraphState) -> dict[str, Any]:
        return self._invoke_graph(state, resume_payload=None)

    def resume(self, *, thread_id: str, resume_payload: dict[str, Any]) -> dict[str, Any]:
        return self._invoke_graph(None, resume_payload=resume_payload, thread_id=thread_id)

    def _invoke_graph(
        self,
        state: ProjectGraphState | None,
        *,
        resume_payload: dict[str, Any] | None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        actual_thread_id = thread_id or cast(str, state["thread_id"] if state else "")
        connection = sqlite3.connect(self._checkpoint_path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            checkpointer = SqliteSaver(connection)
            checkpointer.setup()
            graph = self._build().compile(checkpointer=checkpointer)
            config: RunnableConfig = {"configurable": {"thread_id": actual_thread_id}}
            payload: ProjectGraphState | Command[Any]
            payload = (
                Command(resume=resume_payload)
                if resume_payload is not None
                else cast(ProjectGraphState, state)
            )
            return cast(dict[str, Any], graph.invoke(payload, config=config))
        finally:
            connection.close()

    def _build(self) -> StateGraph[ProjectGraphState]:
        graph = StateGraph(ProjectGraphState)
        graph.add_node("normalize_idea", self._normalize_idea)
        graph.add_node("route_by_depth", self._route_by_depth)
        graph.add_node("find_information_gaps", self._find_information_gaps)
        graph.add_node("await_user_confirmation", self._await_user_confirmation)
        graph.add_node("diverge_directions", self._diverge_directions)
        graph.add_node("score_and_converge", self._score_and_converge)
        graph.add_node("define_mvp", self._define_mvp)
        graph.add_node("recommend_stack", self._recommend_stack)
        graph.add_node("draft_artifacts", self._draft_artifacts)
        graph.add_node("critic_review", self._critic_review)
        graph.add_node("revise_artifacts", self._revise_artifacts)
        graph.add_node("persist_and_render", self._persist_and_render)

        graph.add_edge(START, "normalize_idea")
        graph.add_edge("normalize_idea", "route_by_depth")
        graph.add_edge("route_by_depth", "find_information_gaps")
        graph.add_edge("find_information_gaps", "await_user_confirmation")
        graph.add_conditional_edges(
            "await_user_confirmation",
            self._after_confirmation,
            {"diverge": "diverge_directions", "mvp": "define_mvp"},
        )
        graph.add_edge("diverge_directions", "score_and_converge")
        graph.add_edge("score_and_converge", "define_mvp")
        graph.add_edge("define_mvp", "recommend_stack")
        graph.add_edge("recommend_stack", "draft_artifacts")
        graph.add_conditional_edges(
            "draft_artifacts",
            self._after_draft,
            {"critic": "critic_review", "persist": "persist_and_render"},
        )
        graph.add_conditional_edges(
            "critic_review",
            self._after_review,
            {"revise": "revise_artifacts", "persist": "persist_and_render"},
        )
        graph.add_edge("revise_artifacts", "critic_review")
        graph.add_edge("persist_and_render", END)
        return graph

    def _execute(self, name: str, state: ProjectGraphState, action: NodeAction) -> NodeResult:
        run_id = state["run_id"]
        if self._repository.get_run(run_id).status == RunStatus.CANCELLED:
            raise RunCancelled(f"Run {run_id} was cancelled")
        started = time.perf_counter()
        self._repository.update_run(run_id, current_node=name)
        self._repository.add_event(run_id=run_id, node=name, event_type="node_started")
        try:
            result = action()
        except GraphInterrupt:
            # LangGraph uses this internal control-flow exception to persist an interrupt.
            # It is an expected pause, not a failed node, so it must not pollute traces.
            raise
        except Exception as exc:
            self._repository.add_event(
                run_id=run_id,
                node=name,
                event_type="node_failed",
                payload={"message": str(exc), "error_type": type(exc).__name__},
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            raise
        self._repository.add_event(
            run_id=run_id,
            node=name,
            event_type="node_completed",
            payload={"updated_fields": sorted(result.keys())},
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return result

    def _generate(
        self,
        schema: type[SchemaT],
        *,
        task: str,
        context: dict[str, object],
        state: ProjectGraphState,
    ) -> SchemaT:
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                return self._model.generate(schema, task=task, context=context)
            except ModelGatewayError as exc:
                if not exc.retryable or attempt == max_attempts:
                    raise
                self._repository.add_event(
                    run_id=state["run_id"],
                    node=state.get("current_stage", "model"),
                    event_type="model_retry",
                    payload={"attempt": attempt, "reason": str(exc)},
                )
                time.sleep(0.25 * (2 ** (attempt - 1)))
        raise AssertionError("unreachable")

    def _normalize_idea(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            idea = " ".join(state["raw_idea"].split())
            facts = [f"项目想法：{idea}", f"开发深度：{state['depth']}"]
            if state.get("instruction"):
                facts.append(f"补充要求：{state['instruction']}")
            return {"raw_idea": idea, "known_facts": facts, "current_stage": "normalize_idea"}

        return self._execute("normalize_idea", state, action)

    def _route_by_depth(self, state: ProjectGraphState) -> NodeResult:
        return self._execute(
            "route_by_depth",
            state,
            lambda: {
                "depth_policy": policy_for(state["depth"]).to_state(),
                "current_stage": "route_by_depth",
                "revision_count": 0,
            },
        )

    def _find_information_gaps(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            result = self._generate(
                ClarificationResult,
                task="识别会实质影响 MVP 的信息缺口，并提出少量澄清问题",
                context={
                    "raw_idea": state["raw_idea"],
                    "known_facts": state.get("known_facts", []),
                    "max_questions": state["depth_policy"]["max_questions"],
                },
                state=state,
            )
            return {
                "known_facts": result.known_facts,
                "assumptions": result.assumptions,
                "clarifying_questions": [item.model_dump(mode="json") for item in result.questions],
                "current_stage": "find_information_gaps",
            }

        return self._execute("find_information_gaps", state, action)

    def _await_user_confirmation(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            response = interrupt(
                {
                    "type": "scope_confirmation",
                    "questions": state.get("clarifying_questions", []),
                    "known_facts": state.get("known_facts", []),
                    "assumptions": state.get("assumptions", []),
                }
            )
            if not isinstance(response, dict) or not response.get("confirm_scope", False):
                raise ValueError("用户尚未确认项目范围")
            answers = {
                str(key): str(value).strip()
                for key, value in dict(response.get("answers", {})).items()
                if str(value).strip()
            }
            return {
                "user_answers": answers,
                "scope_confirmed": True,
                "current_stage": "await_user_confirmation",
            }

        return self._execute("await_user_confirmation", state, action)

    def _after_confirmation(self, state: ProjectGraphState) -> str:
        return "diverge" if state["depth_policy"]["enable_divergence"] else "mvp"

    def _diverge_directions(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            result = self._generate(
                DirectionOptions,
                task="基于已确认范围生成差异明确的项目方向，不得扩大首版边界",
                context=self._model_context(state),
                state=state,
            )
            return {
                "candidate_directions": [
                    item.model_dump(mode="json") for item in result.directions
                ],
                "current_stage": "diverge_directions",
            }

        return self._execute("diverge_directions", state, action)

    def _score_and_converge(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            result = self._generate(
                DirectionSelection,
                task="依据用户价值、个人可交付性和技术展示价值选择一个方向",
                context=self._model_context(state),
                state=state,
            )
            return {
                "selected_direction": result.model_dump(mode="json"),
                "current_stage": "score_and_converge",
            }

        return self._execute("score_and_converge", state, action)

    def _define_mvp(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            result = self._generate(
                MvpPlan,
                task="定义有明确边界和可验证指标的 MVP",
                context=self._model_context(state),
                state=state,
            )
            return {"mvp": result.model_dump(mode="json"), "current_stage": "define_mvp"}

        return self._execute("define_mvp", state, action)

    def _recommend_stack(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            if state["depth"] == "spark":
                stack = ["选择团队最熟悉且能最快验证 MVP 的技术"]
            else:
                stack = [
                    "FastAPI：异步 API 与结构化 Schema",
                    "LangGraph：状态图、人工中断与恢复",
                    "SQLite：本地持久化与零运维",
                    "React + Tauri：轻量桌面工作台",
                ]
            return {"recommended_stack": stack, "current_stage": "recommend_stack"}

        return self._execute("recommend_stack", state, action)

    def _draft_artifacts(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            result = self._generate(
                ProjectPlan,
                task="生成与开发深度、确认范围和 MVP 一致的结构化项目方案",
                context=self._model_context(state),
                state=state,
            )
            result.mvp = MvpPlan.model_validate(state["mvp"])
            return {"plan": result.model_dump(mode="json"), "current_stage": "draft_artifacts"}

        return self._execute("draft_artifacts", state, action)

    def _after_draft(self, state: ProjectGraphState) -> str:
        return "critic" if int(state["depth_policy"]["critic_rounds"]) > 0 else "persist"

    def _critic_review(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            result = self._generate(
                ReviewResult,
                task="检查范围回流、术语矛盾、不可验证指标和技术冲突",
                context={**self._model_context(state), "plan": state["plan"]},
                state=state,
            )
            return {"review": result.model_dump(mode="json"), "current_stage": "critic_review"}

        return self._execute("critic_review", state, action)

    def _after_review(self, state: ProjectGraphState) -> str:
        review = ReviewResult.model_validate(state["review"])
        max_rounds = int(state["depth_policy"]["critic_rounds"])
        if review.passed or state.get("revision_count", 0) >= max_rounds:
            return "persist"
        return "revise"

    def _revise_artifacts(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            result = self._generate(
                ProjectPlan,
                task="仅修复评审指出的问题，保留已确认范围和其他正确内容",
                context={
                    **self._model_context(state),
                    "current_plan": state["plan"],
                    "review": state["review"],
                    "revision_count": state.get("revision_count", 0) + 1,
                },
                state=state,
            )
            result.mvp = MvpPlan.model_validate(state["mvp"])
            return {
                "plan": result.model_dump(mode="json"),
                "revision_count": state.get("revision_count", 0) + 1,
                "current_stage": "revise_artifacts",
            }

        return self._execute("revise_artifacts", state, action)

    def _persist_and_render(self, state: ProjectGraphState) -> NodeResult:
        def action() -> NodeResult:
            plan = ProjectPlan.model_validate(state["plan"])
            rendered = render_artifacts(plan)
            allowed = set(cast(list[str], state["depth_policy"]["artifact_types"]))
            selected = {key: value for key, value in rendered.items() if key in allowed}
            saved = self._repository.save_artifacts(
                bubble_id=state["bubble_id"], run_id=state["run_id"], artifacts=selected
            )
            return {
                "current_stage": "persist_and_render",
                "artifacts": [item.model_dump(mode="json") for item in saved],
            }

        return self._execute("persist_and_render", state, action)

    def _model_context(self, state: ProjectGraphState) -> dict[str, object]:
        return {
            "bubble_name": state["bubble_name"],
            "raw_idea": state["raw_idea"],
            "depth": state["depth"],
            "instruction": state.get("instruction"),
            "known_facts": state.get("known_facts", []),
            "assumptions": state.get("assumptions", []),
            "user_answers": state.get("user_answers", {}),
            "candidate_directions": state.get("candidate_directions", []),
            "selected_direction": state.get("selected_direction", {}),
            "recommended_stack": state.get("recommended_stack", []),
            "revision_count": state.get("revision_count", 0),
        }


def extract_interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", first)
    return cast(dict[str, Any], value) if isinstance(value, dict) else {"value": value}
