# Office PC setup (Ryzen 5 3400G, ~14GB usable RAM, no NVIDIA GPU, Windows + WSL2)

Recommended path: **WSL2 (Ubuntu)** - identical to the dev environment, which is what was tested.
A native-Windows alternative (`scripts/setup_office_pc.ps1`) exists but is untested.

## 0. Before you start
- Internet needed once (~2GB LLM + ~4.5GB search models + ~1GB packages). Free disk: >= 15GB.
- Get the code: `git clone git@github.com:TanveerAhmedIvan/office-mind-ai.git` (private repo needs SSH key / token),
  or copy the folder by USB **without** `.venv/` and `qdrant_data/`.
- Faster: copy `~/.cache/huggingface` from the dev PC to skip the 4.5GB download.

## 1. Give WSL enough RAM (IMPORTANT)
WSL2 defaults to 50% of RAM (~7GB) - too little. Create `C:\Users\<you>\.wslconfig`:
```
[wsl2]
memory=11GB
processors=4
swap=4GB
```
Then in PowerShell: `wsl --shutdown`, and reopen Ubuntu. Check: `free -g` shows >= 10.

## 2. Install and test
```bash
cd /path/to/office-mind-ai
bash scripts/setup_wsl.sh            # sudo password prompt; ~15-30 min first time
```
Ends with 27 passing tests and a hardware report - **send that report back**.

## 3. Run
```bash
bash scripts/run_wsl.sh              # http://localhost:8000
```
Other PCs on the LAN (WSL2 does not expose ports to the LAN by default). Pick one:
- Windows 11 22H2+: add `networkingMode=mirrored` under `[wsl2]` in `.wslconfig`, `wsl --shutdown`.
- Windows 10 / older: in **Admin PowerShell** (replace `<WSL-IP>` from `wsl hostname -I`):
  ```
  netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=<WSL-IP>
  New-NetFirewallRule -DisplayName "OfficeMind AI" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
  ```
  (the WSL IP changes after reboot; re-run the first command). There is **no login yet** - LAN only, never the internet.

## 4. Benchmark (decides the model size)
```bash
.venv/bin/python -m eval.bench qwen2.5:3b 4     # forces CPU, 4 threads
LLM_MODEL=qwen2.5:3b .venv/bin/python -m eval.run_eval --no-judge   # accuracy, ~10+ min on CPU
```
Compare candidates: `ollama pull qwen3:4b` / `gemma3:4b`, then `eval.bench <model> 4` (untested for Bangla).

## Performance reality (measured on the dev PC, Ryzen 7 9700X, CPU forced, 4 threads, qwen2.5:3b)
| step | time |
|---|---|
| retrieval incl. rerank | ~4s |
| LLM first token / total | ~5s / ~7s |
| end-to-end | **~11s** |
Earlier "~5s" figures were measured on the RTX 4060 and do NOT apply to the office PC. The 3400G is older/slower:
expect roughly 1.5-2.5x -> **~15-25s per answer**. Levers: rerank fewer chunks (pool 16 -> 8), send top 3 chunks,
smaller reranker, keep Ollama model loaded (`OLLAMA_KEEP_ALIVE=1h`). RAM: ~3.5GB app + ~2.5GB model.

## Troubleshooting
- `ollama: command not found` after install -> `curl -fsSL https://ollama.com/install.sh | sh` needs `zstd` (script installs it).
- Ollama not reachable -> `ollama serve &`, check `curl localhost:11434/api/tags`.
- Out of memory / killed -> raise `.wslconfig` memory, close other apps, or use `LLM_MODEL=qwen2.5:1.5b`.
- Index missing -> `.venv/bin/python -m app.vector build`.
