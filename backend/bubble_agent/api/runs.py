from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from bubble_agent.api.dependencies import Services, get_services, require_local_token
from bubble_agent.domain.schemas import RunCreate, RunEventRead, RunRead, RunResume, RunStatus

router = APIRouter(
    prefix="/api",
    tags=["runs"],
    dependencies=[Depends(require_local_token)],
)


@router.post(
    "/bubbles/{bubble_id}/runs",
    response_model=RunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_run(
    bubble_id: str,
    payload: RunCreate,
    services: Services = Depends(get_services),
) -> RunRead:
    return services.orchestrator.create_and_start(bubble_id, payload)


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(run_id: str, services: Services = Depends(get_services)) -> RunRead:
    return services.repository.get_run(run_id)


@router.post("/runs/{run_id}/resume", response_model=RunRead, status_code=status.HTTP_202_ACCEPTED)
def resume_run(
    run_id: str,
    payload: RunResume,
    services: Services = Depends(get_services),
) -> RunRead:
    return services.orchestrator.resume(run_id, payload)


@router.post("/runs/{run_id}/cancel", response_model=RunRead)
def cancel_run(run_id: str, services: Services = Depends(get_services)) -> RunRead:
    return services.orchestrator.cancel(run_id)


@router.get("/runs/{run_id}/events/history", response_model=list[RunEventRead])
def event_history(
    run_id: str,
    after_id: int = Query(default=0, ge=0),
    services: Services = Depends(get_services),
) -> list[RunEventRead]:
    services.repository.get_run(run_id)
    return services.repository.list_events(run_id, after_id=after_id)


@router.get("/runs/{run_id}/events")
async def stream_events(
    request: Request,
    run_id: str,
    after_id: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    services: Services = Depends(get_services),
) -> EventSourceResponse:
    services.repository.get_run(run_id)
    cursor = max(after_id, int(last_event_id or 0))

    async def generate() -> AsyncIterator[ServerSentEvent]:
        nonlocal cursor
        idle_ticks = 0
        terminal = {RunStatus.WAITING, RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
        while True:
            if await request.is_disconnected():
                break
            events = await asyncio.to_thread(services.repository.list_events, run_id, cursor)
            for event in events:
                cursor = event.id
                yield ServerSentEvent(
                    data=json.dumps(event.model_dump(mode="json"), ensure_ascii=False),
                    event=event.event_type,
                    id=str(event.id),
                )
            run = await asyncio.to_thread(services.repository.get_run, run_id)
            if run.status in terminal and not events:
                yield ServerSentEvent(
                    data=json.dumps(run.model_dump(mode="json"), ensure_ascii=False),
                    event="run_status",
                    id=str(cursor),
                )
                break
            idle_ticks += 1
            if idle_ticks % 30 == 0:
                yield ServerSentEvent(comment="keep-alive")
            await asyncio.sleep(0.2)

    return EventSourceResponse(generate())
