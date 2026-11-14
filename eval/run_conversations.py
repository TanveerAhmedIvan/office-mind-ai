"""Run eval/conversation_tests.json through the real pipeline; print answers for review."""
import json, time
from pathlib import Path
from app.chat import guarded_answer as answer, trim
from app.llm import OllamaLLM

llm = OllamaLLM()
for conv in json.loads((Path(__file__).parent / "conversation_tests.json").read_text(encoding="utf-8")):
    print(f"\n=== {conv['id']}")
    hist = []
    for t in conv["turns"]:
        s = time.time()
        meta, toks = answer(hist, t["user"], llm)
        a = "".join(toks)
        hist = trim(hist + [{"role": "user", "content": t["user"]}, {"role": "assistant", "content": a}])
        print(f"U: {t['user']}\n   rewritten: {meta['standalone']}\n   A: {a}\n   expected: {t['expected']}  ({time.time()-s:.1f}s)")
