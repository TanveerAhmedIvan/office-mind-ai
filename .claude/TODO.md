# TODO  (legend: [ ] todo, [~] in progress, [x] done)

## M0 Setup
- [x] Import kit (data/, eval/, docs/), .gitignore, requirements.txt
- [x] Working venv (.venv) with pdfplumber, pypdf, pytest
## M1 Ingestion  (branch feat/m1-ingestion)
- [x] Parse 11 md files + PDF (tables as own markdown chunk, table text removed from prose)
- [x] Heading-aware chunker, tables intact, superseded flag
- [x] CLI (python -m app.ingest) + 5 passing pytest tests
## M2 Vector search (feat/m2-vector)
- [x] Embedder (bge-m3, CPU, env-configurable), Qdrant local-mode index, top-5 query (app/vector.py), 3 tests
## M3 Hybrid + rerank (feat/m3-hybrid)
- [x] rank_bm25 w/ code-aware tokenizer, RRF, bge-reranker-v2-m3, superseded penalty (app/hybrid.py), 7 tests
## M4 Chat (feat/m4-chat)
- [x] Code: rewrite, prompt builder, Ollama client, FastAPI SSE, HTML UI, 6-turn memory (fake-LLM tests pass)
- [x] Verified with real Ollama qwen2.5:3b: 9/9 conversation turns correct (eval/run_conversations.py). Some answers lack [file] citation -> M5
## M5 Guardrails (feat/m5-guardrails)
- [x] Injection lines stripped at ingest (sanitize), leak guard (canned refusal, no LLM call), low-relevance guard (0.03), fenced context, prompt rules; 5 tests
- [ ] OPEN: Q38 'Is Enterprise plan free?' answers 'I don't know' (expected No/custom quote). 3B model confused by FAQ 'free trial'. Try contextual retrieval / bigger model; see M6 score
## M6 Evaluation (feat/m6-eval)
- [ ] eval script: retrieval hit rate + LLM-judged correctness; report in `eval/reports/`
## Stretch
- [ ] contextual retrieval, debug panel, metadata filter, feedback log, calculate_expense_approval tool

## Open items
- [ ] User to run PowerShell hardware query on office PC (storage, Windows version) -> update docs/hardware.md
- [ ] Benchmark embed/rerank/LLM latency + RAM on CPU; choose LLM size (1.5B vs 3B) by eval score vs speed
