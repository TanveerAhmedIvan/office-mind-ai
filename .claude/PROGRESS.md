# Progress Log
- 2026-11-14: Created SUMMARY/TODO; imported kit; repo initialized on `main`.
- 2026-11-14: M1 (branch feat/m1-ingestion): app/ingest.py + tests written. Markdown chunking verified (stdlib only).
- 2026-11-14: venv fixed after apt install. M1 done: 5/5 tests pass, 47 chunks (45 md + 2 PDF). Merged to main.
- 2026-11-14: Hardware spec received; target is CPU-only office PC. Using CPU torch for M2.
- 2026-11-14: M2 done. bge-m3 on CPU, 47 chunks indexed (index build ~4 min incl. 2.2GB model download), ~0.18s/query after load, ~5s cold start.
  Vector-only doc-level hit@5 = 36/36 (100%) - easy at doc level with 12 docs; chunk-level/answer eval is M6.
  FINDING: superseded leave policy ranks #1 for "annual leave" (0.72 vs handbook 0.67) -> must down-rank superseded in M3 and instruct LLM in M5.
  TODO: compare nomic-embed-text vs bge-m3 (brief asks), measure RAM.
