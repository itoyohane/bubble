from __future__ import annotations

from conftest import wait_for_status
from fastapi.testclient import TestClient

from bubble_agent.config import Settings
from bubble_agent.main import create_app


def test_waiting_run_resumes_after_application_restart(settings: Settings) -> None:
    with TestClient(create_app(settings)) as first_client:
        bubble = first_client.post(
            "/api/bubbles",
            json={
                "name": "Recovery project",
                "raw_idea": "做一个能够在应用重启后恢复运行状态的项目规划 Agent",
                "depth": "builder",
            },
        ).json()
        run = first_client.post(f"/api/bubbles/{bubble['id']}/runs", json={}).json()
        waiting = wait_for_status(first_client, run["id"], {"waiting", "failed"})
        assert waiting["status"] == "waiting", waiting
        checkpoint_db = settings.checkpoint_path
        assert checkpoint_db.exists()

    with TestClient(create_app(settings)) as second_client:
        persisted = second_client.get(f"/api/runs/{run['id']}").json()
        assert persisted["status"] == "waiting"
        questions = persisted["interrupt_payload"]["questions"]
        answers = {question["id"]: "采用推荐值" for question in questions}
        response = second_client.post(
            f"/api/runs/{run['id']}/resume",
            json={"answers": answers, "confirm_scope": True},
        )
        assert response.status_code == 202
        completed = wait_for_status(second_client, run["id"], {"completed", "failed"})
        assert completed["status"] == "completed", completed
