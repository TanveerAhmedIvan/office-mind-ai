# TODO  (legend: [ ] todo, [~] in progress, [x] done)

## M0 Setup
- [~] Import kit (data/, eval/, docs/), .gitignore, README, venv + requirements, project layout `app/`, `tests/`
## M1 Ingestion  (branch feat/m1-ingestion)
- [ ] Parse 11 md files + PDF (tables) -> normalized text
- [ ] Heading-aware chunker, keep tables intact, metadata (source, section, superseded flag)
- [ ] CLI to print chunks; tests (all 12 files present, PDF table captured, Bangla preserved)
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
