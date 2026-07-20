from __future__ import annotations

from bubble_agent.domain.schemas import ProjectPlan


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 暂无"


def render_artifacts(plan: ProjectPlan) -> dict[str, tuple[dict[str, object], str]]:
    summary = plan.summary
    prd = f"""# {summary.name} — PRD

## 一句话定位

{summary.one_liner}

## 背景与问题

{summary.problem}

## 目标用户

{_bullets(summary.target_users)}

## 项目目标

{_bullets(summary.goals)}

## 关键假设

{_bullets(summary.assumptions)}
"""

    mvp = plan.mvp
    mvp_markdown = f"""# MVP 范围

## 验证目标

{mvp.objective}

## 必须包含

{_bullets(mvp.must_have)}

## 时间允许再做

{_bullets(mvp.nice_to_have)}

## 本版不做

{_bullets(mvp.out_of_scope)}

## 成功指标

{_bullets(mvp.success_metrics)}
"""

    artifacts: dict[str, tuple[dict[str, object], str]] = {
        "prd": (summary.model_dump(mode="json"), prd.strip() + "\n"),
        "mvp": (mvp.model_dump(mode="json"), mvp_markdown.strip() + "\n"),
    }

    if plan.user_stories or plan.tech_stack:
        story_blocks = []
        for index, story in enumerate(plan.user_stories, start=1):
            story_blocks.append(
                f"### US-{index:02d}\n\n作为{story.role}，我希望{story.want}，从而{story.benefit}。"
                f"\n\n验收标准：\n{_bullets(story.acceptance_criteria)}"
            )
        stack_rows = "\n".join(
            f"| {item.layer} | {item.technology} | {item.rationale} | {item.alternative or '—'} |"
            for item in plan.tech_stack
        )
        technical = f"""# 技术与交付方案

## 用户故事

{chr(10).join(story_blocks) if story_blocks else '暂无'}

## 技术栈

| 层级 | 选择 | 理由 | 备选 |
| --- | --- | --- | --- |
{stack_rows if stack_rows else '| — | — | — | — |'}

## 风险

{_bullets(plan.risks)}

## 开发里程碑

{_bullets(plan.milestones)}
"""
        artifacts["technical_plan"] = (
            {
                "user_stories": [item.model_dump(mode="json") for item in plan.user_stories],
                "tech_stack": [item.model_dump(mode="json") for item in plan.tech_stack],
                "risks": plan.risks,
                "milestones": plan.milestones,
            },
            technical.strip() + "\n",
        )

    if plan.data_entities or plan.api_draft or plan.test_strategy:
        entity_rows = "\n".join(
            f"| {item.name} | {item.purpose} | {', '.join(item.key_fields)} |"
            for item in plan.data_entities
        )
        api_rows = "\n".join(
            f"| {item.method} | `{item.path}` | {item.purpose} |" for item in plan.api_draft
        )
        architecture = f"""# 深入设计草案

## 数据实体

| 实体 | 用途 | 关键字段 |
| --- | --- | --- |
{entity_rows if entity_rows else '| — | — | — |'}

## API 草案

| 方法 | 路径 | 用途 |
| --- | --- | --- |
{api_rows if api_rows else '| — | — | — |'}

## 测试策略

{_bullets(plan.test_strategy)}
"""
        artifacts["architecture_draft"] = (
            {
                "data_entities": [item.model_dump(mode="json") for item in plan.data_entities],
                "api_draft": [item.model_dump(mode="json") for item in plan.api_draft],
                "test_strategy": plan.test_strategy,
            },
            architecture.strip() + "\n",
        )

    return artifacts
