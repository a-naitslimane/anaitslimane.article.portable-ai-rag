import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from core.database import get_db_connection
from core.ollama_utils import ensure_models

from .routes import router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_models(config.EMBED_MODEL, config.LLM_GEN_MODEL)
    app.state.db = get_db_connection()
    yield

app = FastAPI(title="Portable AI Lab - UI Server", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.include_router(router)

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))