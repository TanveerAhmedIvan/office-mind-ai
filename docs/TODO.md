# TODO

Legend: [x] done, [ ] open. Branch: `feat/architecture-and-session-persistence`.
Rule: after any change to chunking, embeddings or prompts, rerun `python -m eval.run_eval`.

## In progress
- [ ] T1 Persistent chat sessions (SQLite, `chat_data/sessions.db`, gitignored)
  - [ ] store module with load, append, trim to 6 turns, expire old sessions
  - [ ] `server.py` uses the store instead of the `SESSIONS` dict
  - [ ] tests for persistence across a restart and for trimming
  - [ ] config: `SESSION_DB`, `SESSION_TTL_DAYS`

## Next
- [ ] T2 `GET /sessions/{id}` to reload a conversation; UI restores the id from localStorage
- [ ] T3 Debug panel in the UI showing chunks and scores (data is already in the `meta` event)
- [ ] T4 Thumbs up/down feedback, logged to SQLite
- [ ] T5 Login (needs user list) and per-user session ownership
- [ ] T6 Metadata filter by department (needs document-to-department map)
- [ ] T7 `calculate_expense_approval(amount)` tool (needs thresholds from the PDF)
- [ ] T8 Reduce CPU latency on the office PC: rerank pool 16 to 8, top 3 chunks, `OLLAMA_KEEP_ALIVE=1h`
- [ ] T9 Re-enable the relevance guard once a better threshold exists (needs more labelled Bangla data)
- [ ] T10 Run the benchmark on the office PC and record the report

## Data needed from the user
See section 5 of `docs/ARCHITECTURE.html`: user list and roles, department-to-document map, office PC disk and Windows version, expense thresholds, real documents, session retention rule.
