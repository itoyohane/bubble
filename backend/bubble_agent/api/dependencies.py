from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException, Query, Request, status

from bubble_agent.config import Settings
from bubble_agent.persistence.repositories import Repository
from bubble_agent.services.orchestrator import RunOrchestrator


@dataclass(slots=True)
class Services:
    settings: Settings
    repository: Repository
    orchestrator: RunOrchestrator


def get_services(request: Request) -> Services:
    return request.app.state.services


def require_local_token(
    request: Request,
    x_bubble_token: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> None:
    settings: Settings = request.app.state.services.settings
    expected = settings.api_token
    if expected is None:
        return
    supplied = x_bubble_token or token
    if supplied is None or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid local token")
