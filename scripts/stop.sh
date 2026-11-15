#!/usr/bin/env bash
# Stop everything: chat server, unload the model from RAM, and (with --all) the Ollama service itself.
#   bash scripts/stop.sh          chat server + unload model
#   bash scripts/stop.sh --all    also stop Ollama (needs sudo)
cd "$(dirname "$0")/.."
PORT="${PORT:-8001}"
pid=$(ss -ltnp 2>/dev/null | grep ":$PORT " | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
if [ -n "$pid" ]; then kill "$pid" && echo "Chat server stopped (pid $pid)"; else echo "Chat server: not running"; fi
rm -f run/server.pid

if curl -s -m 2 localhost:11434/api/version >/dev/null; then
  for m in $(curl -s localhost:11434/api/ps | grep -o '"name":"[^"]*"' | cut -d'"' -f4); do
    ollama stop "$m" && echo "Model unloaded: $m"
  done
  if [ "$1" = "--all" ]; then
    sudo systemctl stop ollama && echo "Ollama stopped"
  else
    echo "Ollama service left running (idle, tiny RAM). Use --all to stop it."
  fi
fi
