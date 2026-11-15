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
- [x] Relevance guard now OFF by default (broke romanized Bangla); see PROGRESS
- [ ] OPEN: Q38 'Is Enterprise plan free?' answers 'I don't know' (expected No/custom quote). 3B model confused by FAQ 'free trial'. Try contextual retrieval / bigger model; see M6 score
## M6 Evaluation (feat/m6-eval)
- [x] eval/run_eval.py: hit@5 + fact-matching grader (yes/no core-claim, refusal check, hard rules for Q38/Q40/18-vs-15); JSON reports in eval/reports/
- [ ] OPEN (post-M6): Q15 partial (no 'wait/retry'), Q17 SEC-EXC 'I don't know', Q30 omits 31 March, Q33 omits guest price 200, Q38 'I don't know'. Ideas: contextual retrieval, qwen2.5:7b on dev PC, answer-completeness prompt, nomic vs bge-m3 comparison
## Post-M6 work (branch feat/architecture-and-session-persistence)
- [x] docs/ARCHITECTURE.html: visual of indexing + 9-step chat flow, files, sessions, status, missing data
- [x] T1 Persistent chat sessions (SQLite chat_data/sessions.db, 6 turns, 30-day expiry), 4 tests
- [ ] T2 GET /sessions/{id}; UI restores session id from localStorage
- [ ] T3 Debug panel (chunks + scores; already in the `meta` SSE event)
- [ ] T4 Thumbs up/down feedback log (SQLite)
- [ ] T5 Login + per-user sessions. Users: admin@nodi.tech (admin), ivan@nodi.tech (user). Sign-in method TBD
- [ ] T6 Department metadata filter (needs document -> department map)
- [ ] T7 calculate_expense_approval(amount) tool (needs thresholds from the PDF)
- [ ] T9 Re-enable relevance guard with a better threshold (needs labelled Bangla data)

## Stretch
- [ ] contextual retrieval, debug panel, metadata filter, feedback log, calculate_expense_approval tool

## Open items
- [ ] User to run PowerShell hardware query on office PC (storage, Windows version) -> update docs/hardware.md
- [ ] Benchmark embed/rerank/LLM latency + RAM on CPU; choose LLM size (1.5B vs 3B) by eval score vs speed

## Office PC deployment (THIS machine: Ryzen 5 3400G, 8 threads, 1TB disk, WSL2)
- [x] docs/OFFICE_PC_SETUP.md, scripts/setup_wsl.sh, run_wsl.sh, setup_office_pc.ps1 (untested), eval/bench.py
- [x] Setup done here: venv, index (qdrant_data), Ollama + qwen2.5:3b pulled (2026-11-15), 4 session/server tests pass
- [ ] FIX: WSL has only ~6GB RAM and no C:\Users\<you>\.wslconfig -> WSL restarts under load. Set memory=11GB, processors=4, swap=4GB, then `wsl --shutdown`
- [ ] Run jobs ONE AT A TIME (server smoke test, then eval); eval was killed at 6/40 (Q05 medical certificate wrong so far)
- [ ] Record `eval.bench qwen2.5:3b 4` output and CPU latency per answer
- [ ] Decide model (3B vs 4B candidates) from CPU latency + Bangla accuracy; consider cutting rerank pool
- [ ] LAN access (mirrored networking or portproxy) + add auth before sharing with staff
