from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.db.init_db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Persistent Sales Assistant", version="1.0.0")
    app.include_router(router)
    return app


init_db()
app = create_app()

