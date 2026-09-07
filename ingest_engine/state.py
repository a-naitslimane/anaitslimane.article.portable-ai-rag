import json
import os

import config


def load_existing_manifest():
    if os.path.exists(config.MANIFEST_PATH):
        with open(config.MANIFEST_PATH, "r") as f:
            return json.load(f)
    return {}


def save_manifest_state(manifest):
    with open(config.MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=4)


def purge_removed_files(vdb, manifest, tracked_files):
    deleted_files = [p for p in manifest if p not in tracked_files]
    if deleted_files:
        print(f"Purging {len(deleted_files)} files from database...")
        vdb.purge_files(deleted_files)
        for p in deleted_files:
            del manifest[p]