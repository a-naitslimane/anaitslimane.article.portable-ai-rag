from datetime import datetime, timezone

import ollama

import config
from core.ollama_utils import ensure_models
from core.vectors import normalize


def ensure_embedding_models_ready():
    ensure_models(config.EMBED_MODEL, pull_if_missing=True)


def generate_chunk_vector_record(chunk, r_path, mode):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    resp = ollama.embeddings(model=config.EMBED_MODEL, prompt=chunk)
    vector = normalize(resp["embedding"])
    
    return {
        "vector": vector,
        "text": chunk,
        "file_path": r_path,
        "category": mode,
        "timestamp": timestamp,
    }