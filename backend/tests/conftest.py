from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from bubble_agent.config import Settings
from bubble_agent.main import create_app


@pytest.fixture
def settings() -> Settings:
    data_dir = Path.cwd() / "test-data" / str(uuid4())
    data_dir.mkdir(parents=True, exist_ok=False)
    return Settings(data_dir=data_dir, default_provider="demo", default_model="bubble-demo-v1")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def wait_for_status(
    client: TestClient,
    run_id: str,
    expected: set[str],
    *,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        response.raise_for_status()
        last = response.json()
        if last["status"] in expected:
            return last
        time.sleep(0.05)
    raise AssertionError(f"Run did not reach {expected}; last response: {last}")
