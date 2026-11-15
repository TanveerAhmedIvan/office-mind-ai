#!/usr/bin/env bash
# Start Ollama (if needed) and OfficeMind AI inside WSL.   bash scripts/run_wsl.sh [model] [port]
cd "$(dirname "$0")/.."
export LLM_MODEL="${1:-qwen2.5:3b}"; PORT="${2:-8001}"
pgrep -x ollama >/dev/null || (nohup ollama serve >/tmp/ollama.log 2>&1 &) ; sleep 2
echo "Model $LLM_MODEL -> http://localhost:$PORT"
exec .venv/bin/uvicorn app.server:app --host 0.0.0.0 --port "$PORT"
