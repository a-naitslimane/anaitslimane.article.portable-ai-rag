import os
import sys

import lancedb
from lancedb.pydantic import LanceModel, Vector

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import config

DB_PATH = config.DB_PATH
MANIFEST_PATH = config.MANIFEST_PATH
TABLE_NAME = config.TABLE_NAME
EMBED_DIM = config.EMBED_DIM


class ChunkSchema(LanceModel):
    file_path: str
    text: str
    vector: Vector(config.EMBED_DIM)
    category: str
    timestamp: str


class DatabaseEmptyError(Exception):
    pass


def get_db_connection():
    db = lancedb.connect(DB_PATH)
    try:
        db.create_table(TABLE_NAME, schema=ChunkSchema)
    except ValueError:
        pass
    return db


def get_or_create_table(db: lancedb.DBConnection):
    try:
        return db.open_table(TABLE_NAME)
    except Exception:
        return db.create_table(TABLE_NAME, schema=ChunkSchema)


def get_table(db: lancedb.DBConnection):
    table = get_or_create_table(db)
    if len(table) == 0:
        raise DatabaseEmptyError("Knowledge base is empty. Run sync first.")
    return table


class VectorDB:
    def __init__(self):
        self.db = get_db_connection()
        self.table_name = TABLE_NAME

    def purge_files(self, file_paths):
        table = get_or_create_table(self.db)
        for path in file_paths:
            safe_path = path.replace("'", "''")
            table.delete(f"file_path = '{safe_path}'")

    def upsert(self, data_payload):
        if not data_payload:
            return
        table = get_or_create_table(self.db)
        table.add(data_payload)