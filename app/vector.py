"""M2: embed chunks into Qdrant (local on-disk mode) and run top-k vector search."""
from __future__ import annotations
import hashlib, sys, time
from functools import lru_cache
from qdrant_client import QdrantClient, models
from . import config
from .ingest import Chunk, ingest_all


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(config.EMBED_MODEL, device=config.EMBED_DEVICE)


def embed(texts: list[str], batch_size: int = 8) -> list[list[float]]:
    return get_model().encode(texts, batch_size=batch_size, normalize_embeddings=True,
                              show_progress_bar=False).tolist()


def _point_id(chunk_id: str) -> int:
    return int(hashlib.md5(chunk_id.encode()).hexdigest()[:15], 16)


def get_client() -> QdrantClient:
    return QdrantClient(path=config.QDRANT_PATH)


def build_index(chunks: list[Chunk] | None = None, client: QdrantClient | None = None) -> int:
    chunks = chunks or ingest_all()
    client = client or get_client()
    vecs = embed([c.text for c in chunks])
    if client.collection_exists(config.COLLECTION):
        client.delete_collection(config.COLLECTION)
    client.create_collection(config.COLLECTION, vectors_config=models.VectorParams(
        size=len(vecs[0]), distance=models.Distance.COSINE))
    client.upsert(config.COLLECTION, points=[
        models.PointStruct(id=_point_id(c.id), vector=v, payload=c.__dict__)
        for c, v in zip(chunks, vecs)])
    return len(chunks)


def search(query: str, k: int = 5, client: QdrantClient | None = None, allowed: set[str] | None = None) -> list[dict]:
    """allowed: restrict to these source files (None = all)."""
    if allowed is not None and not allowed:
        return []
    client = client or get_client()
    flt = None if allowed is None else models.Filter(must=[models.FieldCondition(
        key="source", match=models.MatchAny(any=sorted(allowed)))])
    res = client.query_points(config.COLLECTION, query=embed([query])[0], limit=k, query_filter=flt,
                              with_payload=True).points
    return [{"score": p.score, **p.payload} for p in res]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        t = time.time(); n = build_index()
        print(f"indexed {n} chunks in {time.time()-t:.1f}s")
    else:
        q = " ".join(sys.argv[1:])
        t = time.time()
        for r in search(q):
            print(f"{r['score']:.3f}  {r['id']}  {r['section']}")
        print(f"({time.time()-t:.2f}s)")
