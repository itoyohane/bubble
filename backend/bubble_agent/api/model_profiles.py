from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from bubble_agent.api.dependencies import require_local_token
from bubble_agent.domain.schemas import (
    ClarificationResult,
    ModelTestRequest,
    ModelTestResponse,
)
from bubble_agent.models.base import StructuredModel
from bubble_agent.models.demo import DemoStructuredModel
from bubble_agent.models.openai_compatible import OpenAICompatibleStructuredModel

router = APIRouter(
    prefix="/api/model-profiles",
    tags=["models"],
    dependencies=[Depends(require_local_token)],
)


@router.post("/test", response_model=ModelTestResponse)
def test_model(payload: ModelTestRequest) -> ModelTestResponse:
    started = time.perf_counter()
    model: StructuredModel
    if payload.provider == "demo":
        model = DemoStructuredModel()
    else:
        if not payload.base_url or not payload.api_key:
            return ModelTestResponse(
                ok=False,
                provider=payload.provider,
                model_name=payload.model_name,
                latency_ms=0,
                message="base_url 和 api_key 为必填项",
            )
        model = OpenAICompatibleStructuredModel(
            provider=payload.provider,
            model_name=payload.model_name,
            base_url=payload.base_url,
            api_key=payload.api_key,
        )
    try:
        model.generate(
            ClarificationResult,
            task="返回一个用于连通性测试的澄清问题",
            context={"raw_idea": "测试连接", "max_questions": 1},
        )
        return ModelTestResponse(
            ok=True,
            provider=payload.provider,
            model_name=payload.model_name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            message="模型连接与结构化输出校验成功",
        )
    except Exception as exc:
        return ModelTestResponse(
            ok=False,
            provider=payload.provider,
            model_name=payload.model_name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            message=str(exc),
        )
