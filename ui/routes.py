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
        "hello", "hi", "hey", "good morning", "good evening",
        "yo", "thanks", "thank you", "just a simple talk",
    }
    cleaned = text.lower().strip()
    return cleaned in greetings


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
        "distance_threshold": getattr(config, "DISTANCE_THRESHOLD", "unknown"),
        "status": "success"
    }


@router.post("/query")
async def handle_query(request: QueryRequest, table=Depends(get_db_table)):
    final_top_k = get_final_top_k(request.top_k, request.question)

    configs = {
        "code": {
            "filter": None,
            "persona": "Strict Structural Code Auditor",
            "instruction": "Identify structural issues, parameter mismatches, type inconsistencies, and refactoring ghosts. Report each finding as: [file.ext] `symbol`: description.",
        },
        "doc": {
            "filter": None,
            "persona": "Technical Project Manager",
            "instruction": "Describe architecture, component responsibilities, and data flows. Use the indexed sources as the sole reference.",
        },
        "auto": {
            "filter": None,
            "persona": "AI Research Assistant",
            "instruction": "Synthesize findings across all indexed sources. Cross-reference files when relevant.",
        },
    }
    active = configs.get(request.category, configs["auto"])
    client = AsyncClient()

    if is_conversational(request.question):
        sources = []
        context = ""
    else:
        try:
            embed_model = getattr(config, "EMBED_MODEL")
            resp = await client.embeddings(model=embed_model, prompt=request.question)
            query_vec = resp["embedding"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding Error: {str(e)}")

        search = table.search(query_vec)

        raw_results = search.limit(final_top_k).to_list()

        distance_threshold = getattr(config, "DISTANCE_THRESHOLD", 1.2)

        results = [r for r in raw_results if r.get("_distance", float("inf")) < distance_threshold]

        if not results and raw_results:
            distances = [round(r.get("_distance", -1), 4) for r in raw_results[:5]]
            print(f"[QUERY] All {len(raw_results)} results filtered out. Top distances: {distances}. Threshold: {distance_threshold}")

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

        try:
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
        except Exception as e:
            yield f"\n\n⚠️ Generation error: {str(e)}"

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