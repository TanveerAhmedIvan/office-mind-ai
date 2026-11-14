"""Thin Ollama client (HTTP). Swappable: anything with .chat(messages, stream) works."""
from __future__ import annotations
import json
from typing import Iterator
import httpx
from . import config


class OllamaLLM:
    def __init__(self, model: str | None = None, url: str | None = None):
        self.model, self.url = model or config.LLM_MODEL, (url or config.OLLAMA_URL).rstrip("/")

    def chat(self, messages: list[dict], stream: bool = True, temperature: float = 0.1) -> Iterator[str]:
        body = {"model": self.model, "messages": messages, "stream": stream,
                "options": {"temperature": temperature}}
        with httpx.stream("POST", f"{self.url}/api/chat", json=body, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    d = json.loads(line)
                    if d.get("message", {}).get("content"):
                        yield d["message"]["content"]
