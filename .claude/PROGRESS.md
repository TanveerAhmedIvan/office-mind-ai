# Progress Log
- 2026-11-14: Created SUMMARY/TODO; imported kit; repo initialized on `main`.
- 2026-11-14: M1 (branch feat/m1-ingestion): app/ingest.py + tests written. Markdown chunking verified (stdlib only).
- 2026-11-14: venv fixed after apt install. M1 done: 5/5 tests pass, 47 chunks (45 md + 2 PDF). Merged to main.
- 2026-11-14: Hardware spec received; target is CPU-only office PC. Using CPU torch for M2.
- 2026-11-14: M2 done. bge-m3 on CPU, 47 chunks indexed (index build ~4 min incl. 2.2GB model download), ~0.18s/query after load, ~5s cold start.
  Vector-only doc-level hit@5 = 36/36 (100%) - easy at doc level with 12 docs; chunk-level/answer eval is M6.
  FINDING: superseded leave policy ranks #1 for "annual leave" (0.72 vs handbook 0.67) -> must down-rank superseded in M3 and instruct LLM in M5.
  TODO: compare nomic-embed-text vs bge-m3 (brief asks), measure RAM.
- 2026-11-14: M3 done. hybrid (BM25+vector, RRF, rerank pool 16) hit@5 = 36/36 (strict: all expected sources). ND-1042 -> error_codes #1; annual leave -> handbook #1 (superseded x0.5 penalty).
  Cost on dev CPU: ~4.5s/query (rerank dominates), peak RSS ~3.7GB. Office PC likely 2-3x slower -> consider reranking fewer candidates (8-10) or a smaller reranker; benchmark on office PC.
  Note: first Q34 miss was caused by too-small rerank pool (10); fixed with 16.
- 2026-11-14: M4 code on feat/m4-chat (app/llm.py, chat.py, server.py, static/index.html); 6 fake-LLM tests pass. NOT merged: no Ollama here (localhost + WSL host:11434 unreachable), so conversation_tests unverified.
- 2026-11-14: Ollama + qwen2.5:3b installed by user. M4 verified: conv tests 9/9 correct; ~5s/answer on dev CPU (first call 48s model load). Merged M4. Gaps: missing citations on some answers; C1 t3 omitted 'no carry forward'.
- 2026-11-14: M5: guardrails 5/6 on Q35-40 (Q38 open). Injection no longer reaches LLM; before fix Q38 said 'free' and Q40 leaked 'Enterprise is free'. Relevance threshold 0.03 is fragile (gap 0.019..0.039).
