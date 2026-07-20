from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from bubble_agent.agents.policies import policy_for
from bubble_agent.config import Settings
from bubble_agent.domain.schemas import Depth
from bubble_agent.main import create_app

ROOT = Path(__file__).resolve().parent


def wait_for_status(
    client: TestClient,
    run_id: str,
    expected: set[str],
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        response.raise_for_status()
        last = response.json()
        if last["status"] in expected:
            return last
        time.sleep(0.03)
    raise TimeoutError(f"run {run_id} timed out; last={last}")


def run_case(client: TestClient, case: dict[str, str]) -> dict[str, Any]:
    depth = Depth(case["depth"])
    policy = policy_for(depth)
    started = time.monotonic()
    checks: dict[str, bool] = {}
    error: str | None = None
    run_id = ""

    try:
        response = client.post(
            "/api/bubbles",
            json={"name": case["name"], "raw_idea": case["idea"], "depth": depth.value},
        )
        response.raise_for_status()
        bubble = response.json()

        response = client.post(f"/api/bubbles/{bubble['id']}/runs", json={})
        response.raise_for_status()
        run_id = response.json()["id"]
        waiting = wait_for_status(client, run_id, {"waiting", "failed"})
        checks["interrupt"] = waiting["status"] == "waiting"

        questions = (waiting.get("interrupt_payload") or {}).get("questions", [])
        checks["question_budget"] = 0 < len(questions) <= policy.max_questions
        answers = {
            question["id"]: question.get("suggested_answer") or "采用建议方案"
            for question in questions
        }
        response = client.post(
            f"/api/runs/{run_id}/resume",
            json={"answers": answers, "confirm_scope": True},
        )
        response.raise_for_status()
        completed = wait_for_status(client, run_id, {"completed", "failed"})
        checks["completed"] = completed["status"] == "completed"

        artifacts = client.get(f"/api/bubbles/{bubble['id']}/artifacts").json()
        artifact_types = {item["artifact_type"] for item in artifacts}
        checks["artifact_contract"] = artifact_types == set(policy.artifact_types)
        checks["nonempty_markdown"] = all(len(item["markdown"].strip()) >= 80 for item in artifacts)

        events = client.get(f"/api/runs/{run_id}/events/history").json()
        completed_nodes = [
            event["node"] for event in events if event["event_type"] == "node_completed"
        ]
        node_counts = Counter(completed_nodes)
        checks["no_node_failure"] = all(event["event_type"] != "node_failed" for event in events)
        checks["depth_route"] = (
            ("diverge_directions" in completed_nodes) == policy.enable_divergence
            and node_counts["critic_review"] >= policy.critic_rounds
        )
    except Exception as exc:  # evaluation must report every failed sample
        error = f"{type(exc).__name__}: {exc}"

    passed = sum(checks.values())
    total = 7
    return {
        "id": case["id"],
        "depth": depth.value,
        "score": round(passed / total, 4),
        "checks": checks,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "run_id": run_id,
        "error": error,
    }


def markdown_report(results: list[dict[str, Any]]) -> str:
    average = sum(item["score"] for item in results) / len(results)
    perfect = sum(item["score"] == 1 for item in results)
    durations = sorted(item["duration_ms"] for item in results)
    p95 = durations[min(len(durations) - 1, int(len(durations) * 0.95))]
    check_names = [
        "interrupt",
        "question_budget",
        "completed",
        "artifact_contract",
        "nonempty_markdown",
        "no_node_failure",
        "depth_route",
    ]
    lines = [
        "# Bubble Agent 离线评测报告",
        "",
        (
            "> 评测使用确定性 Demo Provider，目标是验证工作流、深度策略、产物契约和"
            "恢复边界；它不代表线上大模型的语义质量。"
        ),
        "",
        "## 摘要",
        "",
        f"- 样本数：{len(results)}",
        f"- 全项通过：{perfect}/{len(results)}",
        f"- 平均契约得分：{average:.1%}",
        f"- P95 端到端耗时：{p95} ms",
        "",
        "## 检查维度",
        "",
        (
            "1. 进入人工确认中断；2. 澄清问题不超过深度预算；3. 正常完成；"
            "4. 产物类型符合策略；5. Markdown 非空；6. 无节点失败；"
            "7. 分支与 Critic 路径符合深度策略。"
        ),
        "",
        "## 样本结果",
        "",
        "| 样本 | 深度 | 得分 | 耗时 | 失败项 |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for result in results:
        failed = [name for name in check_names if not result["checks"].get(name, False)]
        if result["error"]:
            failed.append(result["error"])
        lines.append(
            f"| {result['id']} | {result['depth']} | {result['score']:.0%} | "
            f"{result['duration_ms']} ms | {', '.join(failed) or '—'} |"
        )
    lines.extend(
        [
            "",
            "## 如何解读",
            "",
            (
                "该评测把可确定验证的工程契约与主观的内容质量分开。接入真实模型后，"
                "应新增人工或 LLM-as-judge 维度，例如问题相关性、MVP 可执行性、"
                "技术栈论证质量与幻觉率，并保留本报告作为回归基线。"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Bubble Agent offline contract evaluations")
    parser.add_argument("--cases", type=Path, default=ROOT / "cases.json")
    parser.add_argument("--report", type=Path, default=ROOT / "latest_report.md")
    parser.add_argument("--json", type=Path, default=ROOT / "latest_results.json")
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    runtime_dir = ROOT / ".runtime" / str(uuid4())
    runtime_dir.mkdir(parents=True)
    settings = Settings(
        data_dir=runtime_dir,
        default_provider="demo",
        default_model="bubble-demo-v1",
    )
    try:
        with TestClient(create_app(settings)) as client:
            results = [run_case(client, case) for case in cases]
        args.report.write_text(markdown_report(results), encoding="utf-8")
        args.json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        shutil.rmtree(runtime_dir, ignore_errors=True)

    average = sum(item["score"] for item in results) / len(results)
    print(f"{len(results)} cases, average contract score {average:.1%}")
    if average < 1:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
