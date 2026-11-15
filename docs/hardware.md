# Hardware (from user, 2026-11-14)

| | Dev PC | Office PC (deployment target) |
|---|---|---|
| CPU | Ryzen 7 9700X, 8C/16T | Ryzen 5 3400G, 4C/8T |
| GPU | RTX 4060 8GB (CUDA) | Vega 11 iGPU, no CUDA |
| RAM | 32GB DDR5 | ~16GB (13.95GB usable) |
| Storage | 1TB NVMe | unknown (TODO: run PowerShell query on office PC) |
| OS | Windows | Windows (version unknown) |

Office PC role: host Ollama + small model, FastAPI, knowledge base; serve over office LAN; auth/permissions; chat history.
Dev PC role: develop/evaluate pipeline, larger-model experiments.

## Design consequences
- Everything must run CPU-only on the office PC: CPU torch, small quantized LLM (Qwen2.5 1.5B/3B Q4), watch bge-m3 + reranker RAM (~2.5GB + ~2.3GB).
- Evaluate latency on CPU; GPU is a dev-only speedup. Embeddings are computed once at index time.
- Pending from user: output of PowerShell hardware query from the office PC.

## Verified on the office PC (2026-11-15, from inside WSL)
Ryzen 5 3400G (8 threads), 1TB disk (897G free), WSL2 kernel 6.18, **WSL RAM only ~6GB (no .wslconfig)** -> set memory=11GB.
