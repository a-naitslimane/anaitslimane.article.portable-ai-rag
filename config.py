DB_PATH = "./data/vector_store"
SOURCE_DIR = "./data/source_files"
MANIFEST_PATH = "./data/ingestion_manifest.json"
TABLE_NAME = "knowledge_base"

EMBED_MODEL = "snowflake-arctic-embed:m-long"
EMBED_DIM = 768

LLM_GENERATION_MODELS = {
    "code": "deepseek-coder-v2:16b-lite-instruct-q5_K_M",
    "doc":  "mistral-nemo:12b",
    "auto": "mistral-nemo:12b",
}

CHUNK_SIZE = 3500
CHUNK_OVERLAP = 800
TOP_K = 50

DISTANCE_THRESHOLD = 1.2

SKIP_DIRS = {
    'node_modules', 'platforms', '.migration_backup', 'hooks',
    'vendor', '.gradle', '.venv', 'bin', 'obj', 'dist',
    'build', 'target', '.git', '.vs', '.idea', '__pycache__',
    'cache', 'bundles', 'var', 'logs',
    'drawable', 'mipmap-anydpi-v26', 'values',
    '.venv', 'venv', 'env', '__pypackages__', '.env'
}

SKIP_FILES = {
    'package-lock.json', 'yarn.lock', 'composer.lock', 'packages.lock.json',
    '.DS_Store', 'Thumbs.db', 'LICENSE',
    '.env'
}

MEDIA_EXTS = {'.mp3', '.wav', '.mp4', '.mkv', '.mov', '.avi', '.png', '.jpg', '.jpeg', '.gif'}