import datetime
import json
import os
import sys

import ollama

from core.ollama_utils import ensure_models
from core.vectors import normalize

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config
from core.database import VectorDB

from .processors import read_file_content


def run_ingest():
    ensure_models(config.EMBED_MODEL, pull_if_missing=True)
    
    # Setup
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    manifest = {}
    if os.path.exists(config.MANIFEST_PATH):
        with open(config.MANIFEST_PATH, 'r') as f:
            manifest = json.load(f)
    
    vdb = VectorDB()
    
    to_index = []
    current_files = {}

    # 1. SCAN & CATEGORIZE
    print(f"  Starting Strict Scan in: {config.SOURCE_DIR}")
    for root, dirs, files in os.walk(config.SOURCE_DIR):
        dirs[:] = [d for d in dirs if d not in config.SKIP_DIRS]
        
        rel_root = os.path.relpath(root, config.SOURCE_DIR)
        mode = rel_root.split(os.sep)[0].lower() if rel_root != "." else "general"

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            
            # --- AGGRESSIVE NOISE FILTER ---
            is_minified = '.min.' in file
            is_map_file = ext == '.map'
            is_lock_file = file in {'package-lock.json', 'yarn.lock', 'composer.lock', 'packages.lock.json'}
            
            if is_minified or is_map_file or is_lock_file:
                continue

            if file in config.SKIP_FILES or ext in {'.log', '.pem', '.key', '.tmp', '.bak'}:
                continue

            f_path = os.path.join(root, file)
            r_path = os.path.relpath(f_path, config.SOURCE_DIR).replace(os.sep, '/')

            if mode == "code" and ext in config.MEDIA_EXTS:
                continue
            
            stat = os.stat(f_path)
            
            # Skip files larger than 1MB
            if stat.st_size > 1024 * 1024:
                print(f"Skipping {r_path}: File too large ({round(stat.st_size/1024)} KB)")
                continue

            info = {"mtime": stat.st_mtime, "size": stat.st_size, "mode": mode}
            current_files[r_path] = info

            if r_path not in manifest or manifest[r_path]['mtime'] < info['mtime']:
                to_index.append((f_path, r_path, info, mode))

    # 2. PURGE DELETED FILES
    deleted = [p for p in manifest if p not in current_files]
    if deleted:
        print(f"Purging {len(deleted)} files from database...")
        vdb.purge_files(deleted)
        for p in deleted:
            del manifest[p]

    # 3. PROCESS CHANGES
    if not to_index:
        print("No changes detected. Database is synchronized.")
    else:
        print(f"Syncing {len(to_index)} files using {config.EMBED_MODEL}...")
        payload = []
        
        c_size = getattr(config, 'CHUNK_SIZE', 3500)
        c_overlap = getattr(config, 'CHUNK_OVERLAP', 800)

        for idx, (f_path, r_path, info, mode) in enumerate(to_index):
            size_kb = round(info['size'] / 1024, 1)
            print(f"[{idx+1}/{len(to_index)}] Processing: {r_path} ({size_kb} KB)")
            
            if r_path in manifest:
                vdb.purge_files([r_path])
            
            try:
                content = read_file_content(f_path, mode)
            except Exception as e:
                print(f"Error reading {r_path}: {e}")
                continue
            
            if content.strip():
                if len(content) > 1000 and '\n' not in content:
                    print(f"Skipping {r_path}: Minified/Single-line file.")
                    continue

                # --- UPDATED CHUNK LOGIC (1200 chars) ---
                chunks = [content[i:i+c_size] for i in range(0, len(content), c_size - c_overlap)]
                
                for i, chunk in enumerate(chunks):
                    if len(chunks) > 3:
                        print(f"   ∟ Chunk {i+1}/{len(chunks)}...", end="\r")
                                            
                    try:
                        resp = ollama.embeddings(model=config.EMBED_MODEL, prompt=chunk)
                        vector = normalize(resp['embedding'])
                        
                        payload.append({
                            "vector": vector, 
                            "text": chunk, 
                            "file_path": r_path,
                            "category": mode, 
                            "timestamp": timestamp
                        })
                    except Exception as e:
                        print(f"\nEmbedding Error on {r_path} (Chunk {i}): {e}")
                        continue
                
                if len(chunks) > 3:
                    print(f"   {len(chunks)} chunks embedded.      ")

                manifest[r_path] = info

        if payload:
            print(f" Sending {len(payload)} vectors to database...")
            vdb.upsert(payload)

    # 4. SAVE MANIFEST
    with open(config.MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=4)
    print(f"\n Sync Complete. {len(to_index)} updated, {len(deleted)} purged.")