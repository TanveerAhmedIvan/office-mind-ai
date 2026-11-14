# Project Summary: office-mind-ai

RAG chatbot answering questions about the fictional **Nodi Tech Ltd.** using ONLY documents in `data/`.
Spec: `docs/project_brief.md`. Kit notes: `docs/kit_README.md`.

## Requirements
- Every answer cites its source `[file]`; says "I don't know" when docs don't cover it.
- Traps: exact codes (ND-1042, SEC-EXC), tables (md + PDF), superseded leave policy (answer must be 18 days, never 15), Bangla doc, prompt injection in `vendor_notice_printer.md`, out-of-scope questions.

## Architecture
Index: data/ -> parse (md+PDF) -> chunk -> context line -> embed -> vector DB + BM25
Chat: rewrite follow-up -> BM25 + vector -> RRF fuse -> rerank -> top 5 -> prompt (rules + last 6 turns + fenced chunks) -> LLM w/ citations -> stream

## Stack (per brief; swaps recorded in DECISIONS below)
Python + FastAPI, Qdrant, rank_bm25, bge-m3, bge-reranker-v2-m3, Qwen via Ollama, simple HTML UI.

## Targets
Retrieval top-5 hit >= 90%; answer correctness >= 85%; 3/3 out-of-scope + 3/3 guardrail; annual leave = 18.

## Environment findings (2026-11-14)
- WSL2, Python 3.12.3; no Ollama installed; Docker available via Windows; no python deps installed yet.
- ChatGPT share link was not readable (login wall) - brief + kit are the source of truth.

## Workflow rules
- One milestone per branch `feat/mN-...`, merged to `main` with --no-ff after tests pass; commit often.
- Track progress in `.claude/TODO.md` and `.claude/PROGRESS.md`.
- Secrets in `.env` (gitignored). Rerun eval after any chunking/embedding/prompt change.

## DECISIONS
(none yet)
