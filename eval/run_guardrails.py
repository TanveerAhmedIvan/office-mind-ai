"""Print answers for out_of_scope + guardrail questions (Q35-Q40)."""
import csv
from pathlib import Path
from app.chat import guarded_answer as answer
from app.llm import OllamaLLM

llm = OllamaLLM()
for r in csv.DictReader(open(Path(__file__).parent / "eval_questions.csv", encoding="utf-8-sig")):
    if r["type"] in ("out_of_scope", "guardrail"):
        meta, toks = answer([], r["question"], llm)
        print(f"\n{r['id']} [{r['type']}] {r['question']}\n  A: {''.join(toks)}\n  expect: {r['expected_answer']}")
