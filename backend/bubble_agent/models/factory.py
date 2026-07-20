from __future__ import annotations

from bubble_agent.config import Settings
from bubble_agent.models.base import StructuredModel
from bubble_agent.models.demo import DemoStructuredModel
from bubble_agent.models.openai_compatible import OpenAICompatibleStructuredModel


def create_model(settings: Settings) -> StructuredModel:
    if settings.default_provider == "demo":
        return DemoStructuredModel()
    if not settings.model_base_url or not settings.model_api_key:
        raise ValueError(
            "OpenAI-compatible provider requires BUBBLE_AGENT_MODEL_BASE_URL and "
            "BUBBLE_AGENT_MODEL_API_KEY"
        )
    return OpenAICompatibleStructuredModel(
        provider=settings.default_provider,
        model_name=settings.default_model,
        base_url=settings.model_base_url,
        api_key=settings.model_api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )
