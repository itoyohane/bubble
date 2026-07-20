from __future__ import annotations

from typing import cast

from pydantic import BaseModel

from bubble_agent.domain.schemas import (
    ApiDraft,
    ClarificationResult,
    ClarifyingQuestion,
    DataEntity,
    Direction,
    DirectionOptions,
    DirectionSelection,
    MvpPlan,
    ProjectPlan,
    ProjectSummary,
    ReviewIssue,
    ReviewResult,
    StackChoice,
    UserStory,
)
from bubble_agent.models.base import SchemaT


class DemoStructuredModel:
    """Deterministic offline provider used for demos, tests, and interview reliability."""

    provider = "demo"
    model_name = "bubble-demo-v1"

    def generate(
        self,
        schema: type[SchemaT],
        *,
        task: str,
        context: dict[str, object],
    ) -> SchemaT:
        idea = str(context.get("raw_idea", "一个新的软件项目"))
        name = str(context.get("bubble_name", "新项目"))
        depth = str(context.get("depth", "builder"))

        if schema is ClarificationResult:
            max_questions = int(str(context.get("max_questions", 3)))
            candidates = [
                ClarifyingQuestion(
                    id="target_user",
                    question="首版最优先服务哪一类用户？",
                    why_it_matters="目标用户会直接影响功能范围和交互复杂度。",
                    suggested_answer="先聚焦最常遇到该问题的一类个人用户",
                ),
                ClarifyingQuestion(
                    id="success_signal",
                    question="什么结果能证明首版确实有用？",
                    why_it_matters="可验证的结果有助于控制 MVP 范围。",
                    suggested_answer="用户能在 5 分钟内完成一次核心任务",
                ),
                ClarifyingQuestion(
                    id="platform",
                    question="首版必须支持哪些平台或运行环境？",
                    why_it_matters="平台约束会影响技术栈、成本和交付时间。",
                    suggested_answer="先完成单一桌面或 Web 平台",
                ),
                ClarifyingQuestion(
                    id="data_sensitivity",
                    question="项目会处理隐私或敏感数据吗？",
                    why_it_matters="这会改变存储、日志和模型调用策略。",
                    suggested_answer="首版不保存敏感数据",
                ),
                ClarifyingQuestion(
                    id="deadline",
                    question="你希望多久完成可演示版本？",
                    why_it_matters="交付时间决定技术取舍和功能上限。",
                    suggested_answer="4–6 周完成个人可演示版本",
                ),
            ]
            result: BaseModel = ClarificationResult(
                known_facts=[f"用户想做：{idea}"],
                assumptions=["这是一个从 0 到 1 的个人项目"],
                questions=candidates[:max_questions],
            )
        elif schema is DirectionOptions:
            result = DirectionOptions(
                directions=[
                    Direction(
                        name="聚焦核心闭环",
                        summary="优先实现一个从输入到可验证结果的完整流程。",
                        value_score=5,
                        effort_score=2,
                        risk_score=2,
                        rationale="最适合个人项目按期完成并用于演示。",
                    ),
                    Direction(
                        name="强化工程可靠性",
                        summary="在核心功能上增加恢复、校验、评测和运行轨迹。",
                        value_score=4,
                        effort_score=3,
                        risk_score=2,
                        rationale="能够形成更有深度的后端和 Agent 面试素材。",
                    ),
                    Direction(
                        name="扩展平台能力",
                        summary="增加协作、自动执行和外部工具集成。",
                        value_score=3,
                        effort_score=5,
                        risk_score=5,
                        rationale="想象空间大，但不适合作为首版主线。",
                    ),
                ]
            )
        elif schema is DirectionSelection:
            result = DirectionSelection(
                selected_name="强化工程可靠性" if depth != "spark" else "聚焦核心闭环",
                rationale="在可按期交付的前提下，最大化可演示的工程深度。",
            )
        elif schema is MvpPlan:
            result = self._mvp(idea)
        elif schema is ProjectPlan:
            result = self._project_plan(name=name, idea=idea, depth=depth)
        elif schema is ReviewResult:
            revision_count = int(str(context.get("revision_count", 0)))
            if revision_count == 0 and depth != "spark":
                result = ReviewResult(
                    passed=False,
                    issues=[
                        ReviewIssue(
                            severity="medium",
                            path="mvp.success_metrics",
                            problem="需要确保成功指标可以通过产品行为验证。",
                            recommendation="保留带有时间或完成率的量化指标。",
                        )
                    ],
                )
            else:
                result = ReviewResult(passed=True, issues=[])
        else:
            raise ValueError(f"Demo model does not support schema {schema.__name__} for {task}")

        return cast(SchemaT, result)

    def _mvp(self, idea: str) -> MvpPlan:
        return MvpPlan(
            objective=f"围绕“{idea[:60]}”验证一个清晰、可重复的核心使用闭环。",
            must_have=[
                "创建并保存一个项目空间",
                "完成一次核心输入到结果的处理流程",
                "查看、修改并导出结构化结果",
            ],
            nice_to_have=["结果版本对比", "可选的外部工具集成"],
            out_of_scope=["多人实时协作", "自动部署", "复杂权限与计费"],
            success_metrics=[
                "首次用户可在 5 分钟内完成核心流程",
                "固定测试样本的结构化输出成功率达到 95%",
            ],
        )

    def _project_plan(self, *, name: str, idea: str, depth: str) -> ProjectPlan:
        mvp = self._mvp(idea)
        stories: list[UserStory] = []
        stack: list[StackChoice] = []
        risks: list[str] = []
        milestones: list[str] = []
        entities: list[DataEntity] = []
        apis: list[ApiDraft] = []
        tests: list[str] = []

        if depth in {"builder", "architect"}:
            stories = [
                UserStory(
                    role="目标用户",
                    want="从简短想法开始并得到结构化方案",
                    benefit="不用先掌握完整的产品规划方法",
                    acceptance_criteria=[
                        "系统会询问影响范围的关键信息",
                        "用户确认后才生成最终方案",
                    ],
                ),
                UserStory(
                    role="回访用户",
                    want="继续已有项目并查看历史结果",
                    benefit="不需要重复提供背景信息",
                    acceptance_criteria=["应用重启后仍可打开项目与最新产物"],
                ),
            ]
            stack = [
                StackChoice(
                    layer="API",
                    technology="FastAPI",
                    rationale="异步接口、结构化 Schema 与自动文档适合快速构建可靠后端。",
                    alternative="Flask",
                ),
                StackChoice(
                    layer="Agent",
                    technology="LangGraph",
                    rationale="条件路由、人工中断与持久化状态适合长任务工作流。",
                    alternative="手写状态机",
                ),
                StackChoice(
                    layer="Storage",
                    technology="SQLite + SQLAlchemy",
                    rationale="本地优先且零运维，同时保留事务和迁移能力。",
                    alternative="PostgreSQL",
                ),
            ]
            risks = [
                "模型结构化输出在不同供应商之间可能不一致",
                "功能范围膨胀会影响个人项目交付",
                "本地凭据和日志需要避免泄露 API Key",
            ]
            milestones = ["跑通核心后端", "完成 Agent 工作流", "接入桌面工作台", "补齐测试与演示"]

        if depth == "architect":
            entities = [
                DataEntity(
                    name="Project",
                    purpose="保存项目上下文",
                    key_fields=["id", "idea", "depth"],
                ),
                DataEntity(
                    name="Run",
                    purpose="记录一次工作流执行",
                    key_fields=["id", "status", "thread_id"],
                ),
                DataEntity(
                    name="Artifact",
                    purpose="保存版本化产物",
                    key_fields=["type", "version", "schema_data"],
                ),
            ]
            apis = [
                ApiDraft(method="POST", path="/api/projects", purpose="创建项目"),
                ApiDraft(method="POST", path="/api/projects/{id}/runs", purpose="启动工作流"),
                ApiDraft(method="GET", path="/api/runs/{id}/events", purpose="订阅执行事件"),
            ]
            tests = [
                "单元测试覆盖深度路由和结构化校验",
                "集成测试验证中断后重启恢复",
                "固定样本评测范围遵从率与一致性",
            ]

        return ProjectPlan(
            summary=ProjectSummary(
                name=name,
                one_liner=f"将“{idea[:50]}”转化为范围明确、可执行的项目方案。",
                problem="模糊想法直接进入开发容易造成范围膨胀、技术决策不一致和上下文丢失。",
                target_users=["个人开发者", "准备技术面试的学生开发者"],
                goals=["缩短从想法到可执行方案的时间", "保留可追溯的关键决策"],
                assumptions=["首版由单个用户在本地使用"],
            ),
            mvp=mvp,
            user_stories=stories,
            tech_stack=stack,
            risks=risks,
            milestones=milestones,
            data_entities=entities,
            api_draft=apis,
            test_strategy=tests,
        )
