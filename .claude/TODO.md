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
## M6 Evaluation (feat/m6-eval)  STATUS: script done+merged; last run 2026-11-14 hit 97%, correct 88%, guardrails 5/6 (target 6/6 missed: Q38). NOT yet re-run on the office PC (killed at 6/40) -> rerun, then tick
- [x] eval/run_eval.py: hit@5 + fact-matching grader (yes/no core-claim, refusal check, hard rules for Q38/Q40/18-vs-15); JSON reports in eval/reports/
- [ ] OPEN (post-M6): Q15 partial (no 'wait/retry'), Q17 SEC-EXC 'I don't know', Q30 omits 31 March, Q33 omits guest price 200, Q38 'I don't know'. Ideas: contextual retrieval, qwen2.5:7b on dev PC, answer-completeness prompt, nomic vs bge-m3 comparison
## Post-M6 work (branch feat/architecture-and-session-persistence)
- [x] docs/ARCHITECTURE.html: visual of indexing + 9-step chat flow, files, sessions, status, missing data
- [x] T1 Persistent chat sessions (SQLite chat_data/sessions.db, 6 turns, 30-day expiry), 4 tests
- [x] T2 GET /sessions/{id}; UI restores session id from localStorage (test added)
- [x] T3 Debug panel in UI (Debug button: standalone question + chunk scores)
- [x] UI rewrite: dark mode, mobile, New chat, suggestion chips, source chips, error message, send disabled while streaming
- [x] T4 Thumbs up/down feedback: POST /feedback -> SQLite `feedback` table (kept after chat expiry); UI buttons; 2 tests
- [x] T5 Login (email + password, scrypt hash, httpOnly cookie, 12h token). Users admin@nodi.tech (admin), ivan@nodi.tech (user), both password `password` -> CHANGE (UI: Password button; admin can set). Chats owned per user; admin may read any. 
- [x] Sidebar (2026-11-15): previous chats list (title = first question, time, delete), + New chat, daily-limit status panel (used/limit bar, warn at 80%, red at limit). Full chat is now stored (30-day expiry); the model still gets only the last 6 turns. Endpoints GET /sessions, DELETE /sessions/{sid}. Phone: sidebar behind the menu button
- [x] tests/conftest.py: tests use an in-memory DB (a running server locks the real one)
- [x] Per-chat trace view ("How this was answered" under every answer, saved in SQLite, reloadable): 9 steps with file/function, values, ms, timeline bar, files retrieved vs cited, superseded penalty
- [x] Admin page /admin: create/disable/delete users, set role, set password, roles + per-role document permissions (all docs or a list), usage table
- [x] Usage + limits: default 50 messages/user/day (DEFAULT_DAILY_LIMIT), per-user override (0 = unlimited), HTTP 429 when over; usage per user: today/7d/total, approx tokens in/out, last used
- [ ] SECURITY: default password is `password` and the server is on the LAN. Change both passwords before staff use; consider forcing change at first login
- [x] T6 Document permissions per role, enforced inside vector (Qdrant filter) and BM25 search. Seeded roles admin and user = all documents. Departments = roles (create e.g. `hr`, pick its documents)
- [x] T7 calculate_expense_approval (app/tools.py): thresholds read from the PDF (team lead within limit; dept head above a limit; CFO also above BDT 25,000). Called by the pipeline when a question asks about approving a BDT amount; result injected as a cited fact; shown in the trace; skipped if the user may not read the expense PDF. 7 tests
- [x] T9 Investigated, guard stays OFF (2026-11-15, eval/calibrate_guard.py, 50 questions): cosine in-scope min 0.374 vs out-of-scope max 0.623; best cut-off 0.525 gets 46/50 but would refuse 'How much does the Growth plan cost?' (0.485) and romanized Bangla. The LLM refusal rule (prompt rule 3) handles out-of-scope instead. Reranker-score pass not done (~20s/question on this CPU): `python -m eval.calibrate_guard --rerank`

## Stretch
- [ ] contextual retrieval, debug panel, metadata filter, feedback log, calculate_expense_approval tool

## Open items
- [ ] User to run PowerShell hardware query on office PC (storage, Windows version) -> update docs/hardware.md
- [ ] Benchmark embed/rerank/LLM latency + RAM on CPU; choose LLM size (1.5B vs 3B) by eval score vs speed

## Office PC deployment (THIS machine: Ryzen 5 3400G, 8 threads, 1TB disk, WSL2)
- [x] docs/OFFICE_PC_SETUP.md, scripts/setup_wsl.sh, run_wsl.sh, setup_office_pc.ps1 (untested), eval/bench.py
- [x] Setup done here: venv, index (qdrant_data), Ollama + qwen2.5:3b pulled (2026-11-15), 4 session/server tests pass
- [ ] FIX: WSL has only ~6GB RAM and no C:\Users\<you>\.wslconfig -> WSL restarts under load. Set memory=11GB, processors=4, swap=4GB, then `wsl --shutdown`
- [x] .wslconfig applied (10GB / 4 threads). Port 8000 is taken by php8.3 (MOCA app) -> OfficeMind uses 8001 (run_wsl.sh default); portproxy/firewall for 8001 added by user in PowerShell
- [x] Smoke test on 8010: annual leave answer = 18 days, cites employee_handbook_v3.md; first request took 2m16s (cold model load)
- [x] Cold start fix: model preloaded in a background thread at server start (keep_alive 1h)
- [x] SERVER RUNNING 2026-11-15: http://192.168.68.111:8001 (LAN) and http://localhost:8001, started with `setsid nohup uvicorn ... --host 0.0.0.0 --port 8001` (dies on `wsl --shutdown`/reboot -> `bash scripts/run_wsl.sh`). Windows portproxy 8001 -> WSL IP 172.31.154.34 + firewall rule 'OfficeMind AI 8001' present. WSL IP changes after reboot -> re-run the portproxy command.
- [x] Live checks via LAN IP: login OK; annual leave -> 18 days [employee_handbook_v3.md]; 'claimed BDT 30,000' -> Department head + CFO (tool used)
- [ ] LATENCY TOO HIGH (measured warm, 3400G, 4 threads): ~110-155 s per answer vs 15-25 s target. Breakdown: vector ~1 s, BM25 ~0 s, RERANK 38-45 s (16 candidates), LLM first token 52-63 s, generation ~5-10 s. Fix options (T8): rerank pool 16 -> 6-8, smaller/no reranker, 3 chunks, 1.5B model, check Ollama threads; then re-run eval
- [ ] Rerun eval (`python -m eval.run_eval --no-judge`, ~40 q x ~2 min = ~80 min at current speed) AFTER latency fix
- [ ] Run jobs ONE AT A TIME (server smoke test, then eval); eval was killed at 6/40 (Q05 medical certificate wrong so far)
- [ ] Record `eval.bench qwen2.5:3b 4` output and CPU latency per answer
- [ ] Decide model (3B vs 4B candidates) from CPU latency + Bangla accuracy; consider cutting rerank pool
- [ ] LAN access (mirrored networking or portproxy) + add auth before sharing with staff
