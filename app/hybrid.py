"""M3: BM25 + vector search fused with RRF, then cross-encoder rerank."""
from __future__ import annotations
import re, sys, time
from functools import lru_cache
from rank_bm25 import BM25Okapi
from . import config, vector
from .ingest import Chunk, ingest_all

RERANK_MODEL = config.os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
SUPERSEDED_PENALTY = 0.5   # multiplicative on rerank score for outdated documents
RRF_K = 60

_CODE = re.compile(r"[A-Za-z]+-[A-Za-z0-9]+")
_WORD = re.compile(r"[\wঀ-৿]+")


def tokenize(text: str) -> list[str]:
    """Lowercase words; codes like ND-1042 are kept whole AND split, so both match."""
    toks = [m.group(0).lower() for m in _CODE.finditer(text)]
    return toks + [w.lower() for w in _WORD.findall(text)]


@lru_cache(maxsize=1)
def _bm25() -> tuple[BM25Okapi, list[Chunk]]:
    chunks = ingest_all()
    return BM25Okapi([tokenize(c.text) for c in chunks]), chunks


def bm25_search(query: str, k: int = 20, allowed: set[str] | None = None) -> list[tuple[Chunk, float]]:
    bm, chunks = _bm25()
    scores = bm.get_scores(tokenize(query))
    order = sorted((i for i in range(len(chunks)) if allowed is None or chunks[i].source in allowed),
                   key=lambda i: -scores[i])[:k]
    return [(chunks[i], float(scores[i])) for i in order if scores[i] > 0]


def rrf(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    out: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, 1):
            out[cid] = out.get(cid, 0.0) + 1.0 / (k + rank)
    return out


@lru_cache(maxsize=1)
def _reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANK_MODEL, device=config.EMBED_DEVICE)


def hybrid_search(query: str, k: int = 5, rerank: bool = True, pool: int = 20,
                  client=None, allowed: set[str] | None = None) -> list[dict]:
    vec = vector.search(query, pool, client, allowed)
    lex = bm25_search(query, pool, allowed)
    for r in vec:
        r["vscore"] = r["score"]  # keep raw cosine similarity; "score" is overwritten by rerank below
    by_id = {r["id"]: r for r in vec}
    for c, _ in lex:
        by_id.setdefault(c.id, {**c.__dict__, "vscore": 0.0})
    fused = rrf([[r["id"] for r in vec], [c.id for c, _ in lex]])
    cands = sorted(by_id.values(), key=lambda r: -fused[r["id"]])[: max(k * 3, 16)]
    for r in cands:
        r["rrf"] = fused[r["id"]]
    if rerank:
        scores = _reranker().predict([(query, r["text"]) for r in cands])
        for r, s in zip(cands, scores):
            r["score"] = float(s) * (SUPERSEDED_PENALTY if r["superseded"] else 1.0)
    else:
        for r in cands:
            r["score"] = r["rrf"] * (SUPERSEDED_PENALTY if r["superseded"] else 1.0)
    return sorted(cands, key=lambda r: -r["score"])[:k]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]); t = time.time()
    for r in hybrid_search(q):
        print(f"{r['score']:.3f} rrf={r['rrf']:.4f}  {r['id']}  {r['section']}")
    print(f"({time.time()-t:.2f}s)")
