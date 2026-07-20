from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from bubble_agent.config import Settings
from bubble_agent.main import create_app

TOKEN = "test-local-token"
HEADERS = {"X-Bubble-Token": TOKEN}


def make_client() -> TestClient:
    data_dir = Path.cwd() / "test-data" / str(uuid4())
    data_dir.mkdir(parents=True, exist_ok=False)
    return TestClient(
        create_app(
            Settings(
                data_dir=data_dir,
                api_token=TOKEN,
                default_provider="demo",
                default_model="bubble-demo-v1",
            )
        )
    )


def wait_for_status(client: TestClient, run_id: str, expected: set[str]) -> dict[str, object]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}", headers=HEADERS)
        response.raise_for_status()
        run = response.json()
        if run["status"] in expected:
            return run
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach {expected}")


def create_waiting_run(client: TestClient) -> tuple[dict[str, object], dict[str, object]]:
    bubble_response = client.post(
        "/api/bubbles",
        headers=HEADERS,
        json={
            "name": "Security test",
            "raw_idea": "构建一个用于验证本地接口安全和事件恢复行为的桌面 Agent",
            "depth": "spark",
        },
    )
    bubble_response.raise_for_status()
    bubble = bubble_response.json()
    run_response = client.post(
        f"/api/bubbles/{bubble['id']}/runs",
        headers=HEADERS,
        json={},
    )
    run_response.raise_for_status()
    run = wait_for_status(client, run_response.json()["id"], {"waiting", "failed"})
    return bubble, run


def test_local_token_protects_api_and_sse_supports_query_token() -> None:
    with make_client() as client:
        assert client.get("/api/bubbles").status_code == 401
        assert client.get("/api/bubbles", headers={"X-Bubble-Token": "wrong"}).status_code == 401
        assert client.get("/api/bubbles", headers=HEADERS).status_code == 200

        _, run = create_waiting_run(client)
        response = client.get(f"/api/runs/{run['id']}/events?after_id=0&token={TOKEN}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "event: human_input_required" in response.text
        assert "event: run_status" in response.text


def test_cancelled_run_has_terminal_event_and_updates_bubble() -> None:
    with make_client() as client:
        bubble, run = create_waiting_run(client)
        response = client.post(f"/api/runs/{run['id']}/cancel", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

        detail = client.get(f"/api/bubbles/{bubble['id']}", headers=HEADERS).json()
        assert detail["bubble"]["status"] == "cancelled"
        events = client.get(
            f"/api/runs/{run['id']}/events/history",
            headers=HEADERS,
        ).json()
        assert events[-1]["event_type"] == "run_cancelled"
