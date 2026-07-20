from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bubble_agent.api.bubbles import router as bubbles_router
from bubble_agent.api.dependencies import Services
from bubble_agent.api.model_profiles import router as models_router
from bubble_agent.api.runs import router as runs_router
from bubble_agent.config import Settings, get_settings
from bubble_agent.models.factory import create_model
from bubble_agent.persistence.database import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from bubble_agent.persistence.repositories import NotFoundError, Repository
from bubble_agent.services.orchestrator import RunOrchestrator


def create_app(settings: Settings | None = None) -> FastAPI:
    actual_settings = settings or get_settings()
    actual_settings.ensure_directories()
    engine = create_database_engine(actual_settings)
    initialize_database(engine)
    repository = Repository(create_session_factory(engine))
    model = create_model(actual_settings)
    orchestrator = RunOrchestrator(
        settings=actual_settings,
        repository=repository,
        model=model,
    )
    services = Services(
        settings=actual_settings,
        repository=repository,
        orchestrator=orchestrator,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> Any:
        yield
        orchestrator.shutdown()
        engine.dispose()

    app = FastAPI(
        title=actual_settings.app_name,
        version=actual_settings.app_version,
        description="Depth-aware local project planning agent API",
        lifespan=lifespan,
    )
    app.state.services = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:1420", "http://127.0.0.1:1420"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": actual_settings.app_version,
            "provider": model.provider,
            "model": model.model_name,
        }

    app.include_router(bubbles_router)
    app.include_router(runs_router)
    app.include_router(models_router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
