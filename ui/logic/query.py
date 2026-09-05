import json

from fastapi.responses import StreamingResponse
from ollama import AsyncClient

import config

from ..models import QueryRequest
from .code import get_final_top_k
from .personas import PERSONAS
from .prompts import (
    PROMPT_BEHAVIOR_HYBRID,
    PROMPT_BEHAVIOR_STRICT,
    PROMPT_CLASSIFIER,
    PROMPT_CONVERSATIONAL,
    construct_audit_prompt,
)


async def is_conversational(text: str, client: AsyncClient) -> bool:
    try:
        resp = await client.generate(model=config.LLM_GEN_MODEL, prompt=PROMPT_CLASSIFIER.format(question=text))
        return "CONVERSATIONAL" in resp["response"].upper()
    except Exception:
        return False


async def stream_response(client: AsyncClient, prompt: str, sources: list) -> StreamingResponse:
    async def generator():
        yield json.dumps({"sources": sources}) + "\n---\n"
        try:
            buffer = ""
            async for fragment in await client.generate(
                model=config.LLM_GEN_MODEL,
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

    return StreamingResponse(generator(), media_type="text/plain")


async def execute(request: QueryRequest, client: AsyncClient, table) -> StreamingResponse:
    if await is_conversational(request.question, client):
        prompt = PROMPT_CONVERSATIONAL.format(question=request.question)
        return await stream_response(client, prompt, sources=[])

    final_top_k = get_final_top_k(request.top_k, request.question)
    active = PERSONAS.get(request.category, PERSONAS["auto"])

    resp = await client.embeddings(model=config.EMBED_MODEL, prompt=request.question)
    query_vec = resp["embedding"]

    raw_results = table.search(query_vec).limit(final_top_k).to_list()

    distance_threshold = getattr(config, "DISTANCE_THRESHOLD", 1.2)
    results = [r for r in raw_results if r.get("_distance", float("inf")) < distance_threshold]

    if not results and raw_results:
        distances = [round(r.get("_distance", -1), 4) for r in raw_results[:5]]
        print(f"[QUERY] All {len(raw_results)} results filtered out. Top distances: {distances}. Threshold: {distance_threshold}")

    sources = list({r["file_path"] for r in results})
    context = "\n---\n".join([f"Source: {r['file_path']}\n{r['text']}" for r in results])

    behavior = PROMPT_BEHAVIOR_STRICT if request.mode == "strict" else PROMPT_BEHAVIOR_HYBRID
    prompt = construct_audit_prompt(active, behavior, sources, context, request.question)

    return await stream_response(client, prompt, sources)