from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import PlainTextResponse

from bubble_agent.api.dependencies import Services, get_services, require_local_token
from bubble_agent.domain.schemas import (
    ArtifactRead,
    BubbleCreate,
    BubbleRead,
    BubbleUpdate,
)

router = APIRouter(
    prefix="/api/bubbles",
    tags=["bubbles"],
    dependencies=[Depends(require_local_token)],
)


@router.post("", response_model=BubbleRead, status_code=status.HTTP_201_CREATED)
def create_bubble(payload: BubbleCreate, services: Services = Depends(get_services)) -> BubbleRead:
    return services.repository.create_bubble(payload)


@router.get("", response_model=list[BubbleRead])
def list_bubbles(services: Services = Depends(get_services)) -> list[BubbleRead]:
    return services.repository.list_bubbles()


@router.get("/{bubble_id}")
def get_bubble(
    bubble_id: str, services: Services = Depends(get_services)
) -> dict[str, object]:
    bubble = services.repository.get_bubble(bubble_id)
    artifacts = services.repository.list_latest_artifacts(bubble_id)
    runs = services.repository.list_runs(bubble_id)
    return {
        "bubble": bubble.model_dump(mode="json"),
        "artifacts": [item.model_dump(mode="json") for item in artifacts],
        "latest_run": runs[0].model_dump(mode="json") if runs else None,
    }


@router.patch("/{bubble_id}", response_model=BubbleRead)
def update_bubble(
    bubble_id: str,
    payload: BubbleUpdate,
    services: Services = Depends(get_services),
) -> BubbleRead:
    return services.repository.update_bubble(bubble_id, payload)


@router.delete("/{bubble_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bubble(bubble_id: str, services: Services = Depends(get_services)) -> Response:
    services.repository.delete_bubble(bubble_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{bubble_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(
    bubble_id: str, services: Services = Depends(get_services)
) -> list[ArtifactRead]:
    services.repository.get_bubble(bubble_id)
    return services.repository.list_latest_artifacts(bubble_id)


@router.get("/{bubble_id}/artifacts/{artifact_type}", response_model=list[ArtifactRead])
def artifact_versions(
    bubble_id: str,
    artifact_type: str,
    services: Services = Depends(get_services),
) -> list[ArtifactRead]:
    services.repository.get_bubble(bubble_id)
    return services.repository.list_artifact_versions(bubble_id, artifact_type)


@router.get("/{bubble_id}/export", response_class=PlainTextResponse)
def export_bubble(
    bubble_id: str, services: Services = Depends(get_services)
) -> PlainTextResponse:
    bubble = services.repository.get_bubble(bubble_id)
    artifacts = services.repository.list_latest_artifacts(bubble_id)
    sections = [
        f"# {bubble.name}\n",
        f"> 开发深度：{bubble.depth.value}\n",
        f"## 原始想法\n\n{bubble.raw_idea}\n",
    ]
    sections.extend(item.markdown for item in artifacts)
    filename = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in bubble.name)
    return PlainTextResponse(
        "\n---\n\n".join(sections),
        headers={"Content-Disposition": f'attachment; filename="{filename or "bubble"}.md"'},
    )
