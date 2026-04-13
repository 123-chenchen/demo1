from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.api import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="PDF Chatbot Backend",
        version="0.1.0",
        description="CRUD API for authentication, documents, chat sessions, chat messages, and retrieval sources.",
    )

    @app.get("/health", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "app_name": settings.app_name,
        }

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
