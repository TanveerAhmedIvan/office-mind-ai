# TODO  (legend: [ ] todo, [~] in progress, [x] done)

## M0 Setup
- [x] Import kit (data/, eval/, docs/), .gitignore, requirements.txt
- [x] Working venv (.venv) with pdfplumber, pypdf, pytest
## M1 Ingestion  (branch feat/m1-ingestion)
- [x] Parse 11 md files + PDF (tables as own markdown chunk, table text removed from prose)
- [x] Heading-aware chunker, tables intact, superseded flag
- [x] CLI (python -m app.ingest) + 5 passing pytest tests
## M2 Vector search (feat/m2-vector)
- [ ] Embedder interface (bge-m3 default, fallback), Qdrant (local mode) index, top-5 query
## M3 Hybrid + rerank (feat/m3-hybrid)
- [ ] rank_bm25 w/ code-friendly tokenizer, RRF, reranker, ND-1042 test
## M4 Chat (feat/m4-chat)
- [ ] Query rewrite, prompt builder, LLM client (Ollama), FastAPI SSE streaming, HTML UI, last-6-turns memory, conversation_tests
## M5 Guardrails (feat/m5-guardrails)
- [ ] Out-of-scope refusal, injection fencing, no system-prompt leak, prefer current policy
## M6 Evaluation (feat/m6-eval)
- [ ] eval script: retrieval hit rate + LLM-judged correctness; report in `eval/reports/`
## Stretch
- [ ] contextual retrieval, debug panel, metadata filter, feedback log, calculate_expense_approval tool

## Open items
- [ ] User to run PowerShell hardware query on office PC (storage, Windows version) -> update docs/hardware.md
- [ ] Benchmark embed/rerank/LLM latency + RAM on CPU; choose LLM size (1.5B vs 3B) by eval score vs speed
