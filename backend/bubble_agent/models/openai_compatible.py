from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import ValidationError

from bubble_agent.models.base import ModelGatewayError, SchemaT


class OpenAICompatibleStructuredModel:
    """Small provider-neutral adapter for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        *,
        provider: str,
        model_name: str,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds

    def generate(
        self,
        schema: type[SchemaT],
        *,
        task: str,
        context: dict[str, object],
    ) -> SchemaT:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        context_json = json.dumps(context, ensure_ascii=False, default=str)
        payload = {
            "model": self.model_name,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是严谨的产品与技术规划 Agent。只输出一个合法 JSON 对象，"
                        "不得使用 Markdown 代码块。输出必须满足给定 JSON Schema。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"任务：{task}\n上下文：{context_json}\nJSON Schema：{schema_json}",
                },
            ],
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
            if response.status_code in {401, 403}:
                raise ModelGatewayError("模型认证失败，请检查 API Key", retryable=False)
            if response.status_code == 429 or response.status_code >= 500:
                raise ModelGatewayError(
                    f"模型服务暂时不可用（HTTP {response.status_code}）", retryable=True
                )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            content = data["choices"][0]["message"]["content"]
            return schema.model_validate_json(content)
        except ModelGatewayError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ModelGatewayError(f"模型网络错误：{exc}", retryable=True) from exc
        except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise ModelGatewayError(f"模型结构化输出无效：{exc}", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            raise ModelGatewayError(f"模型请求失败：{exc}", retryable=False) from exc
