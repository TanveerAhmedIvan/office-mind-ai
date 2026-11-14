"""Latency/RAM benchmark for the office PC.
  python -m eval.bench [model] [threads]     e.g.  python -m eval.bench qwen2.5:3b 4
Reports: cold start, retrieval time, first-token + total answer time, tokens/s, process RAM."""
import os, sys, time
model = sys.argv[1] if len(sys.argv) > 1 else os.getenv("LLM_MODEL", "qwen2.5:3b")
threads = int(sys.argv[2]) if len(sys.argv) > 2 else None
os.environ["LLM_MODEL"] = model
import httpx
from app import config
from app.chat import build_messages
from app.hybrid import hybrid_search

QS = ["How many days of annual leave do I get?", "What does error ND-1042 mean?",
      "What is the hotel limit outside Dhaka?", "Uttara bus kokhon charhe?", "ক্যান্টিনে দুপুরের খাবারের দাম কত?"]


def rss_mb():
    try:
        import psutil; return psutil.Process().memory_info().rss // 2**20
    except ImportError:
        return -1


t = time.time(); hybrid_search("warmup", 5); print(f"cold start (embed+rerank load): {time.time()-t:.1f}s  RAM {rss_mb()}MB")
rows = []
for q in QS:
    t0 = time.time(); chunks = hybrid_search(q, 5); tr = time.time() - t0
    body = {"model": model, "messages": build_messages([], q, chunks), "stream": True,
            "options": {"temperature": 0.1, "num_gpu": 0, **({"num_thread": threads} if threads else {})}}
    first = None; n = 0; t1 = time.time()
    with httpx.stream("POST", f"{config.OLLAMA_URL}/api/chat", json=body, timeout=600) as r:
        for line in r.iter_lines():
            if line and '"content":""' not in line:
                if first is None: first = time.time() - t1
                n += 1
    tot = time.time() - t1
    rows.append((tr, first or 0, tot, n / max(tot - (first or 0), 1e-6)))
    print(f"{q[:38]:40} retrieve {tr:5.1f}s  first-token {first or 0:5.1f}s  total {tot:5.1f}s  ~{rows[-1][3]:.1f} tok/s")
avg = lambda i: sum(r[i] for r in rows[1:]) / max(len(rows) - 1, 1)  # skip first (model warm-up)
print(f"\nMODEL {model} threads={threads or 'default'} | avg (excl. 1st): retrieve {avg(0):.1f}s, "
      f"first-token {avg(1):.1f}s, answer total {avg(2):.1f}s, end-to-end ~{avg(0)+avg(2):.1f}s | RAM {rss_mb()}MB")
