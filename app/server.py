"""FastAPI: POST /chat streams Server-Sent Events; GET / serves the UI."""
from __future__ import annotations
import json, uuid
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from . import config
from .chat import answer, trim
from .llm import OllamaLLM

app = FastAPI(title="OfficeMind AI")
SESSIONS: dict[str, list[dict]] = {}
llm = OllamaLLM()


class Req(BaseModel):
    message: str
    session_id: str | None = None


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/chat")
def chat(req: Req):
    sid = req.session_id or uuid.uuid4().hex
    history = SESSIONS.setdefault(sid, [])

    def gen():
        meta, tokens = answer(history, req.message, llm)
        yield sse("meta", {**meta, "session_id": sid})
        parts = []
        for t in tokens:
            parts.append(t)
            yield sse("token", t)
        history.extend([{"role": "user", "content": req.message},
                        {"role": "assistant", "content": "".join(parts)}])
        SESSIONS[sid] = trim(history)
        yield sse("done", {})
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent.parent / "static" / "index.html")
