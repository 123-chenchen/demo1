from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api import api_router
from app.core.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def create_app() -> FastAPI:
    settings = get_settings()
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app = FastAPI(
        title="PDF Chatbot Backend",
        version="0.1.0",
        description="CRUD API for authentication, documents, chat sessions, chat messages, and retrieval sources.",
    )

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/demo", status_code=307)

    @app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
    def demo_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "demo.html",
            {
                "app_name": settings.app_name,
            },
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
