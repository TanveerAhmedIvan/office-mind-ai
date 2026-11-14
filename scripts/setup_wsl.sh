#!/usr/bin/env bash
# OfficeMind AI - setup inside WSL (Ubuntu) on the office PC. Safe to re-run.
#   bash scripts/setup_wsl.sh [model]        default model: qwen2.5:3b
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:-qwen2.5:3b}"

echo "== 0. WSL memory check (need >= 10GB; default WSL limit is only 50% of RAM) =="
free -g | sed -n 2p
[ "$(free -g | awk '/Mem:/{print $2}')" -ge 9 ] || echo "WARNING: WSL has <10GB. Create C:\\Users\\<you>\\.wslconfig (see docs/OFFICE_PC_SETUP.md), run 'wsl --shutdown' in PowerShell, reopen."

echo "== 1. System packages (sudo) =="
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip zstd git curl

echo "== 2. Ollama =="
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
pgrep -x ollama >/dev/null || (nohup ollama serve >/tmp/ollama.log 2>&1 &) ; sleep 3
ollama pull "$MODEL"

echo "== 3. Python env (CPU-only torch) =="
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -q -r requirements.txt

echo "== 4. Build index (downloads bge-m3 + reranker ~4.5GB once; or copy ~/.cache/huggingface from dev PC) =="
.venv/bin/python -m app.vector build

echo "== 5. Tests =="
.venv/bin/python -m pytest -q tests

echo "== 6. Hardware report (send back) =="
nproc; free -h | sed -n 2p; lscpu | grep -E "Model name|^CPU\(s\)"; df -h . | tail -1

echo; echo "DONE. Run: bash scripts/run_wsl.sh   then open http://localhost:8000"
echo "Benchmark (CPU): .venv/bin/python -m eval.bench $MODEL 4"
