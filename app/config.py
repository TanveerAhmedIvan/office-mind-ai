import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
QDRANT_PATH = os.getenv("QDRANT_PATH", str(ROOT / "qdrant_data"))
COLLECTION = os.getenv("QDRANT_COLLECTION", "nodi_docs")
EMBED_DEVICE = os.getenv("EMBED_DEVICE", "cpu")  # office PC is CPU-only
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")  # small + CPU-friendly for the office PC
MAX_TURNS = 6
