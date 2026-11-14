import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
QDRANT_PATH = os.getenv("QDRANT_PATH", str(ROOT / "qdrant_data"))
COLLECTION = os.getenv("QDRANT_COLLECTION", "nodi_docs")
EMBED_DEVICE = os.getenv("EMBED_DEVICE", "cpu")  # office PC is CPU-only
