#!/usr/bin/env bash
# Start everything: Ollama (model server) + OfficeMind AI chat server, in the background.
#   bash scripts/start.sh [model] [port]
cd "$(dirname "$0")/.."
export LLM_MODEL="${1:-qwen2.5:3b}"; PORT="${2:-8001}"
mkdir -p run

if ! curl -s -m 2 localhost:11434/api/version >/dev/null; then
  echo "Starting Ollama..."
  sudo systemctl start ollama 2>/dev/null || (setsid nohup ollama serve >run/ollama.log 2>&1 &)
  for _ in $(seq 20); do curl -s -m 1 localhost:11434/api/version >/dev/null && break; sleep 1; done
fi
curl -s -m 2 localhost:11434/api/version >/dev/null && echo "Ollama: running" || { echo "Ollama failed to start"; exit 1; }

if ss -ltn | grep -q ":$PORT "; then
  echo "Chat server: already running on port $PORT"; exit 0
fi
setsid nohup .venv/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port "$PORT" >run/server.log 2>&1 &
echo $! > run/server.pid
for _ in $(seq 60); do curl -s -m 1 -o /dev/null "localhost:$PORT/" && break; sleep 1; done
curl -s -m 1 -o /dev/null "localhost:$PORT/" && echo "Chat server: running -> http://localhost:$PORT  (log: run/server.log)" \
  || echo "Chat server not up yet; see run/server.log"
echo "The model loads into RAM in the background; the first answer may be slow until then."
