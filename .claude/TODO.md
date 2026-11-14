# TODO  (legend: [ ] todo, [~] in progress, [x] done)

## M0 Setup
- [x] Import kit (data/, eval/, docs/), .gitignore, requirements.txt
- [ ] Working venv with pip (BLOCKED: needs `sudo apt install python3-venv python3-pip` or approval to run get-pip.py)
## M1 Ingestion  (branch feat/m1-ingestion)
- [~] Parse 11 md files (done) + PDF tables (code written, untested: needs pdfplumber)
- [x] Heading-aware chunker, tables intact, superseded flag
- [~] CLI (python -m app.ingest) + tests written; pytest not yet runnable
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
