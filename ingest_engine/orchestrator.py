import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config
from core.database import VectorDB

from .chunker import is_unsupported_minified_text, split_text_into_chunks
from .embedder import ensure_embedding_models_ready, generate_chunk_vector_record
from .processors import read_file_content
from .scanner import scan_workspace_for_file_changes
from .state import (
    load_existing_manifest,
    purge_removed_files,
    save_manifest_state,
)


def run_ingest():
    ensure_embedding_models_ready()
    manifest = load_existing_manifest()
    vdb = VectorDB()

    files_to_process, tracked_files = scan_workspace_for_file_changes(manifest)
    purge_removed_files(vdb, manifest, tracked_files)

    if not files_to_process:
        print("No changes detected. Database is synchronized.")
        return

    _vectorize_and_index_modified_files(vdb, manifest, files_to_process)
    save_manifest_state(manifest)



def _vectorize_and_index_modified_files(vdb, manifest, files_to_process):
    print(f"Syncing {len(files_to_process)} files using {config.EMBED_MODEL}...")
    vector_payload = []

    for idx, (f_path, r_path, info, mode) in enumerate(files_to_process):
        size_kb = round(info["size"] / 1024, 1)
        print(f"[{idx+1}/{len(files_to_process)}] Processing: {r_path} ({size_kb} KB)")

        if r_path in manifest:
            vdb.purge_files([r_path])

        try:
            content = read_file_content(f_path, mode)
        except Exception as e:
            print(f"Error reading {r_path}: {e}")
            continue

        if not content.strip() or is_unsupported_minified_text(content):
            continue

        chunks = split_text_into_chunks(content)

        for i, chunk in enumerate(chunks):
            if len(chunks) > 3:
                print(f"   ∟ Chunk {i+1}/{len(chunks)}...", end="\r")

            try:
                record = generate_chunk_vector_record(chunk, r_path, mode)
                vector_payload.append(record)
            except Exception as e:
                print(f"\nEmbedding Error on {r_path} (Chunk {i}): {e}")
                continue

        if len(chunks) > 3:
            print(f"   {len(chunks)} chunks embedded.      ")

        manifest[r_path] = info

    if vector_payload:
        print(f" Sending {len(vector_payload)} vectors to database...")
        vdb.upsert(vector_payload)