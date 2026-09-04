import json
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from ollama import AsyncClient

import config
from core.database import DB_PATH, MANIFEST_PATH, DatabaseEmptyError, get_table

from .logic.code import construct_audit_prompt, get_behavior_guides, get_final_top_k
from .models import QueryRequest

router = APIRouter()


def get_db_table(req: Request):
    try:
        return get_table(req.app.state.db)
    except DatabaseEmptyError as e:
        raise HTTPException(status_code=500, detail=str(e))


def is_conversational(text: str) -> bool:
    greetings = {
        "hello",
        "hi",
        "hey",
        "good morning",
        "good evening",
        "yo",
        "thanks",
        "thank you",
        "just a simple talk",
    }
    cleaned = text.lower().strip()
    return cleaned in greetings or (len(cleaned.split()) <= 2 and cleaned in greetings)

@router.get("/config")
def get_system_config():
    return {
        "source_dir": getattr(config, "SOURCE_DIR", "./data/source_files"),
        "db_path": getattr(config, "DB_PATH", "./data/vector_store"),
        "embed_model": getattr(config, "EMBED_MODEL", "unknown"),
        "embed_dim": getattr(config, "EMBED_DIM", "unknown"),
        "llm_model": getattr(config, "LLM_GEN_MODEL", "unknown"),
        "chunk_size": getattr(config, "CHUNK_SIZE", "unknown"),
        "chunk_overlap": getattr(config, "CHUNK_OVERLAP", "unknown"),
        "top_k": getattr(config, "TOP_K", "unknown"),
        "status": "success"
    }

@router.post("/query")
async def handle_query(request: QueryRequest, table=Depends(get_db_table)):
    final_top_k = get_final_top_k(request.top_k, request.question)

    configs = {
        "code": {
            "filter": "category = 'code'",
            "persona": "Strict Structural Code Auditor",
            "instruction": "Verify parameter names/types between API and Models.",
        },
        "doc": {
            "filter": None,
            "persona": "Technical Project Manager",
            "instruction": "Focus on high-level architecture and system flow documentation.",
        },
        "auto": {
            "filter": None,
            "persona": "AI Research Assistant",
            "instruction": "Synthesize data across all project files.",
        },
    }
    active = configs.get(request.category, configs["auto"])
    client = AsyncClient()

    if is_conversational(request.question):
        sources = []
        context = ""
    else:
        try:
            embed_model = getattr(
                config, "EMBED_MODEL"
            )
            resp = await client.embeddings(
                model=embed_model, prompt=request.question
            )
            query_vec = resp["embedding"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding Error: {str(e)}")

        search = table.search(query_vec)
        if active["filter"]:
            search = search.where(active["filter"])

        results = search.limit(final_top_k).to_list()
        results = [r for r in results if r.get("_distance", 1.0) < 0.6]

        sources = list({r["file_path"] for r in results})
        context = "\n---\n".join(
            [f"Source: {r['file_path']}\n{r['text']}" for r in results]
        )

    prompt = construct_audit_prompt(
        active,
        get_behavior_guides(request.mode),
        sources,
        context,
        request.question,
    )

    async def stream_generator():
        llm_gen_model = getattr(config, "LLM_GEN_MODEL")
        meta = {"sources": sources}
        yield json.dumps(meta) + "\n---\n"

        buffer = ""
        async for fragment in await client.generate(
            model=llm_gen_model,
            prompt=prompt,
            stream=True,
            options={"num_ctx": 4096},
        ):
            if "response" in fragment:
                buffer += fragment["response"]
                if len(buffer) >= 20:
                    yield buffer
                    buffer = ""
        if buffer:
            yield buffer

    return StreamingResponse(stream_generator(), media_type="text/plain")


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