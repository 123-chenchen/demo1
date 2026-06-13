from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.db.session import init_db


# Create the FastAPI app and configure it with CORS and routes
def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.auto_init_db:
            init_db()
        yield

    app = FastAPI(
        title="PDF Chatbot Backend",
        version="0.1.0",
        description="CRUD API for authentication, documents, chat sessions, chat messages, and retrieval sources.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
