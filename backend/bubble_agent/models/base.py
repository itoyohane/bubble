from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredModel(Protocol):
    provider: str
    model_name: str

    def generate(
        self,
        schema: type[SchemaT],
        *,
        task: str,
        context: dict[str, object],
    ) -> SchemaT:
        """Generate and validate one structured response."""


class ModelGatewayError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable
