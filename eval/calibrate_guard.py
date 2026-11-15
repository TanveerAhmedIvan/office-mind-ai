"""T9: measure retrieval scores for in-scope vs out-of-scope questions to pick a relevance-guard threshold.
Retrieval only (no LLM). Usage: python -m eval.calibrate_guard [--rerank]"""
import csv, sys
from pathlib import Path
from app import vector
from app.hybrid import hybrid_search

rows = list(csv.DictReader(open(Path(__file__).parent / "eval_questions.csv", encoding="utf-8-sig")))
EXTRA = [  # extra labelled questions: romanized Bangla (in scope) and clearly out of scope
    ("Uttara bus kokhon charhe?", True), ("Canteen e lunch er dam koto?", True), ("Bus pass kothay pawa jay?", True),
    ("What is the weather in Dhaka today?", False), ("Who won the cricket world cup?", False),
    ("Write me a poem about the sea", False), ("কাল আবহাওয়া কেমন থাকবে?", False), ("বাংলাদেশের রাজধানী কী?", False),
    ("Tell me a joke", False), ("What is 25 times 4?", False)]
data = [(r["question"], r["source_documents"].strip().lower() not in ("", "none", "n/a")) for r in rows] + EXTRA
RERANK = "--rerank" in sys.argv  # slow on CPU (~20s/question); cosine-only pass takes seconds
res = []
for q, inscope in data:
    if RERANK:
        top = hybrid_search(q, 5)
        res.append((q, inscope, max(c["score"] for c in top), max(c["vscore"] for c in top)))
    else:
        top = vector.search(q, 5)
        res.append((q, inscope, 0.0, max(c["score"] for c in top)))
    print(f'{"IN " if inscope else "OUT"} rerank={res[-1][2]:.3f} cos={res[-1][3]:.3f}  {q[:60]}', flush=True)
for name, i in ((("rerank", 2),) if RERANK else ()) + (("cosine", 3),):
    ins = sorted(r[i] for r in res if r[1]); outs = sorted(r[i] for r in res if not r[1])
    print(f"\n{name}: in-scope min={ins[0]:.3f} p10={ins[len(ins)//10]:.3f} | out-of-scope max={outs[-1]:.3f} p90={outs[-1-len(outs)//10]:.3f}")
    best = max(((sum(r[i] >= t for r in res if r[1]) + sum(r[i] < t for r in res if not r[1]), t) for t in [x/200 for x in range(0, 200)]))
    print(f"{name}: best single threshold {best[1]:.3f} classifies {best[0]}/{len(res)} correctly")
