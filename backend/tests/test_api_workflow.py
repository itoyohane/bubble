from __future__ import annotations

from conftest import wait_for_status
from fastapi.testclient import TestClient


def create_bubble(client: TestClient, depth: str) -> dict[str, object]:
    response = client.post(
        "/api/bubbles",
        json={
            "name": f"{depth.title()} project",
            "raw_idea": "做一个帮助学生把模糊想法整理成项目计划的桌面 Agent",
            "depth": depth,
        },
    )
    assert response.status_code == 201
    return response.json()


def run_until_waiting(client: TestClient, bubble_id: str) -> dict[str, object]:
    response = client.post(f"/api/bubbles/{bubble_id}/runs", json={})
    assert response.status_code == 202
    run = response.json()
    return wait_for_status(client, str(run["id"]), {"waiting", "failed"})


def resume_until_done(client: TestClient, run: dict[str, object]) -> dict[str, object]:
    payload = run["interrupt_payload"]
    assert isinstance(payload, dict)
    questions = payload["questions"]
    answers = {
        question["id"]: question.get("suggested_answer") or "按推荐方案"
        for question in questions
    }
    response = client.post(
        f"/api/runs/{run['id']}/resume",
        json={"answers": answers, "confirm_scope": True},
    )
    assert response.status_code == 202
    return wait_for_status(client, str(run["id"]), {"completed", "failed"})


def test_spark_workflow_interrupts_and_generates_two_artifacts(client: TestClient) -> None:
    bubble = create_bubble(client, "spark")
    waiting = run_until_waiting(client, str(bubble["id"]))
    assert waiting["status"] == "waiting", waiting
    assert len(waiting["interrupt_payload"]["questions"]) == 2
    waiting_events = client.get(f"/api/runs/{waiting['id']}/events/history").json()
    assert all(event["event_type"] != "node_failed" for event in waiting_events)

    completed = resume_until_done(client, waiting)
    assert completed["status"] == "completed", completed

    detail = client.get(f"/api/bubbles/{bubble['id']}").json()
    assert {item["artifact_type"] for item in detail["artifacts"]} == {"prd", "mvp"}

    events = client.get(f"/api/runs/{waiting['id']}/events/history").json()
    nodes = {event["node"] for event in events}
    assert "await_user_confirmation" in nodes
    assert "diverge_directions" not in nodes
    assert "critic_review" not in nodes


def test_builder_workflow_runs_divergence_and_critic(client: TestClient) -> None:
    bubble = create_bubble(client, "builder")
    waiting = run_until_waiting(client, str(bubble["id"]))
    assert waiting["status"] == "waiting", waiting
    assert len(waiting["interrupt_payload"]["questions"]) == 5

    completed = resume_until_done(client, waiting)
    assert completed["status"] == "completed", completed

    artifacts = client.get(f"/api/bubbles/{bubble['id']}/artifacts").json()
    assert {item["artifact_type"] for item in artifacts} == {
        "prd",
        "mvp",
        "technical_plan",
    }
    events = client.get(f"/api/runs/{waiting['id']}/events/history").json()
    nodes = [event["node"] for event in events if event["event_type"] == "node_completed"]
    assert "diverge_directions" in nodes
    assert "score_and_converge" in nodes
    assert nodes.count("critic_review") == 2
    assert nodes.count("revise_artifacts") == 1


def test_architect_workflow_generates_deep_artifact(client: TestClient) -> None:
    bubble = create_bubble(client, "architect")
    waiting = run_until_waiting(client, str(bubble["id"]))
    assert waiting["status"] == "waiting", waiting
    assert len(waiting["interrupt_payload"]["questions"]) == 5

    completed = resume_until_done(client, waiting)
    assert completed["status"] == "completed", completed
    artifacts = client.get(f"/api/bubbles/{bubble['id']}/artifacts").json()
    assert {item["artifact_type"] for item in artifacts} == {
        "prd",
        "mvp",
        "technical_plan",
        "architecture_draft",
    }


def test_export_contains_all_latest_artifacts(client: TestClient) -> None:
    bubble = create_bubble(client, "builder")
    waiting = run_until_waiting(client, str(bubble["id"]))
    completed = resume_until_done(client, waiting)
    assert completed["status"] == "completed", completed

    response = client.get(f"/api/bubbles/{bubble['id']}/export")
    assert response.status_code == 200
    assert "# MVP 范围" in response.text
    assert "# 技术与交付方案" in response.text
    assert "多人实时协作" in response.text


def test_unknown_bubble_returns_404(client: TestClient) -> None:
    response = client.get("/api/bubbles/not-a-real-id")
    assert response.status_code == 404
