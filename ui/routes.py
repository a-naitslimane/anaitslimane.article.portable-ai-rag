import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, Request
from ollama import AsyncClient

import config
from core.database import DB_PATH, MANIFEST_PATH, DatabaseEmptyError, get_table

from .logic import query
from .models import QueryRequest

router = APIRouter()


def get_db_table(req: Request):
    try:
        return get_table(req.app.state.db)
    except DatabaseEmptyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
def get_system_config():
    return {
        "source_dir": config.SOURCE_DIR,
        "db_path": config.DB_PATH,
        "embed_model": config.EMBED_MODEL,
        "embed_dim": config.EMBED_DIM,
        "chunk_size": config.CHUNK_SIZE,
        "chunk_overlap": config.CHUNK_OVERLAP,
        "top_k": config.TOP_K,
        "distance_threshold": getattr(config, "DISTANCE_THRESHOLD", 1.2),
        "status": "success"
    }


@router.post("/query")
async def handle_query(request: QueryRequest, table=Depends(get_db_table)):
    client = AsyncClient()
    try:
        return await query.execute(request, client, table)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_memory():
    try:
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)
        if os.path.exists(MANIFEST_PATH):
            os.remove(MANIFEST_PATH)
        return {"status": "success", "message": "Memory wiped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indexed-files")
def get_indexed_files(table=Depends(get_db_table)):
    df = table.to_pandas()
    return {
        "files": sorted(df["file_path"].unique().tolist()) if not df.empty else [],
        "status": "success",
    }