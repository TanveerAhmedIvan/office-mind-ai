"""FastAPI: login, POST /chat (SSE, permission-filtered retrieval), admin API for users/roles/documents."""
from __future__ import annotations
import json, threading, time, uuid
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from . import config
from .auth import AuthStore, TOKEN_TTL, doc_names
from .chat import guarded_answer as answer
from .hybrid import hybrid_search
from . import tools
from .llm import OllamaLLM
from .sessions import SessionStore

STATIC = Path(__file__).parent.parent / "static"
app = FastAPI(title="OfficeMind AI")
store = SessionStore()
store.purge_expired()
auth = AuthStore(store.db)
llm = OllamaLLM()


def warm_llm() -> None:
    """Load the model into RAM at startup so the first user does not wait minutes (CPU cold start)."""
    try:
        import httpx
        httpx.post(f"{config.OLLAMA_URL}/api/generate", timeout=600,
                   json={"model": config.LLM_MODEL, "prompt": "", "keep_alive": "1h"})
    except Exception:
        pass


@app.on_event("startup")
def _startup():
    threading.Thread(target=warm_llm, daemon=True).start()


def current_user(request: Request) -> dict:
    u = auth.user_for_token(request.cookies.get("token"))
    if not u:
        raise HTTPException(401, "login required")
    return u


def admin_user(u: dict = Depends(current_user)) -> dict:
    if u["role"] != "admin":
        raise HTTPException(403, "admin only")
    return u


class Login(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class Req(BaseModel):
    message: str
    session_id: str | None = None


class Feedback(BaseModel):
    session_id: str | None = None
    rating: int  # 1 = thumbs up, -1 = thumbs down
    question: str = ""
    answer: str = ""


class NewUser(BaseModel):
    email: str
    name: str = ""
    password: str
    role: str
    daily_limit: int | None = None


class UserPatch(BaseModel):
    role: str | None = None
    active: bool | None = None
    password: str | None = None
    name: str | None = None
    daily_limit: int | None = None  # 0 = unlimited, -1 = default


class RoleBody(BaseModel):
    all_docs: bool = False
    docs: list[str] = []


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---- auth ----
@app.post("/login")
def login(body: Login, response: Response):
    token = auth.login(body.email, body.password)
    if not token:
        raise HTTPException(401, "wrong email or password")
    response.set_cookie("token", token, httponly=True, samesite="lax", max_age=TOKEN_TTL)
    return auth.user_for_token(token)


@app.post("/logout")
def logout(request: Request, response: Response):
    auth.logout(request.cookies.get("token"))
    response.delete_cookie("token")
    return {"ok": True}


@app.get("/me")
def me(u: dict = Depends(current_user)):
    return {**u, "limit": auth.limit_for(u["email"]), "used_today": auth.used_today(u["email"])}


@app.post("/me/password")
def change_password(body: PasswordChange, u: dict = Depends(current_user)):
    if len(body.new_password) < 8:
        raise HTTPException(400, "new password must be at least 8 characters")
    if not auth.check_password(u["email"], body.old_password):
        raise HTTPException(403, "old password is wrong")
    auth.update_user(u["email"], password=body.new_password)
    return {"ok": True}


# ---- chat ----
@app.post("/chat")
def chat(req: Req, u: dict = Depends(current_user)):
    sid = req.session_id or uuid.uuid4().hex
    if not auth.claim_session(sid, u["email"]):
        raise HTTPException(403, "this chat belongs to another user")
    usage_id = auth.start_usage(u["email"], len(req.message))
    if usage_id is None:
        raise HTTPException(429, f"daily limit of {auth.limit_for(u['email'])} messages reached; try again tomorrow")
    history = store.history(sid)
    allowed = auth.allowed_docs(u["role"])

    found: dict = {}  # filled by hybrid_search with every intermediate result (trace view)

    def search(q, k):
        return hybrid_search(q, k, allowed=allowed, trace=found)

    def gen():
        t0 = time.perf_counter()
        meta, tokens = answer(history, req.message, llm, search,
                              use_tools=allowed is None or tools.SOURCE in allowed)
        t_llm = time.perf_counter()
        yield sse("meta", {**meta, "session_id": sid})
        parts, t_first = [], None
        for t in tokens:
            t_first = t_first or time.perf_counter()
            parts.append(t)
            yield sse("token", t)
        t_end = time.perf_counter()
        full = "".join(parts)
        msg_id = store.append_turn(sid, req.message, full)
        auth.finish_usage(usage_id, len(full))
        ms = lambda a, b: round((a - b) * 1000)
        trace = {"question": req.message, "standalone": meta["standalone"], "guard": meta.get("guard"),
                 "user": u["email"], "role": u["role"], "allowed": None if allowed is None else sorted(allowed),
                 "history_msgs": len(history), "model": getattr(llm, "model", "?"),
                 "rewrite": meta.get("rewrite"), "tool": meta.get("tool"), "retrieval": found.get("retrieval"), "prompt": meta.get("prompt"),
                 "answer_chars": len(full), "limit": auth.limit_for(u["email"]), "used_today": auth.used_today(u["email"]),
                 "ms": {"rewrite": (meta.get("rewrite") or {}).get("ms", 0), "retrieval": meta.get("retrieval_ms", 0),
                        "prepare": ms(t_llm, t0), "first_token": ms(t_first or t_end, t_llm),
                        "llm": ms(t_end, t_llm), "total": ms(t_end, t0)}}
        store.save_trace(sid, msg_id, trace)
        yield sse("trace", {"id": msg_id, **trace})
        yield sse("done", {})
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/feedback")
def feedback(fb: Feedback, u: dict = Depends(current_user)):
    store.add_feedback(fb.session_id, fb.rating, fb.question, fb.answer)
    return {"ok": True}


@app.get("/sessions/{sid}")
def get_session(sid: str, u: dict = Depends(current_user)):
    owner = auth.session_owner(sid)
    if owner and owner != u["email"] and u["role"] != "admin":
        raise HTTPException(403, "this chat belongs to another user")
    return {"session_id": sid, "messages": store.history_with_trace(sid)}


@app.get("/traces/{msg_id}")
def get_trace(msg_id: int, u: dict = Depends(current_user)):
    row = store.get_trace(msg_id)
    if not row:
        raise HTTPException(404, "no trace")
    sid, trace = row
    owner = auth.session_owner(sid)
    if owner and owner != u["email"] and u["role"] != "admin":
        raise HTTPException(403, "this chat belongs to another user")
    return {"id": msg_id, **trace}


# ---- admin ----
@app.get("/admin/docs")
def admin_docs(_: dict = Depends(admin_user)):
    return doc_names()


@app.get("/admin/users")
def admin_users(_: dict = Depends(admin_user)):
    return auth.list_users()


@app.post("/admin/users")
def admin_create_user(b: NewUser, _: dict = Depends(admin_user)):
    if len(b.password) < 8:
        raise HTTPException(400, "password must be at least 8 characters")
    try:
        auth.create_user(b.email, b.name, b.password, b.role, b.daily_limit)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.patch("/admin/users/{email}")
def admin_patch_user(email: str, b: UserPatch, u: dict = Depends(admin_user)):
    if b.password is not None and len(b.password) < 8:
        raise HTTPException(400, "password must be at least 8 characters")
    cur = next((x for x in auth.list_users() if x["email"] == email), None)
    if not cur:
        raise HTTPException(404, "no such user")
    demoting = cur["role"] == "admin" and (b.role not in (None, "admin") or b.active is False)
    if demoting and auth.admin_count() <= 1:
        raise HTTPException(400, "cannot remove the last active admin")
    try:
        auth.update_user(email, b.role, b.active, b.password, b.name, b.daily_limit)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.delete("/admin/users/{email}")
def admin_delete_user(email: str, u: dict = Depends(admin_user)):
    cur = next((x for x in auth.list_users() if x["email"] == email), None)
    if not cur:
        raise HTTPException(404, "no such user")
    if email == u["email"] or (cur["role"] == "admin" and auth.admin_count() <= 1):
        raise HTTPException(400, "cannot delete yourself or the last admin")
    auth.delete_user(email)
    return {"ok": True}


@app.get("/admin/usage")
def admin_usage(_: dict = Depends(admin_user)):
    return auth.usage_report()


@app.get("/admin/roles")
def admin_roles(_: dict = Depends(admin_user)):
    return auth.list_roles()


@app.put("/admin/roles/{name}")
def admin_set_role(name: str, b: RoleBody, _: dict = Depends(admin_user)):
    auth.set_role(name.strip().lower(), b.all_docs, b.docs)
    return {"ok": True}


@app.delete("/admin/roles/{name}")
def admin_delete_role(name: str, _: dict = Depends(admin_user)):
    try:
        auth.delete_role(name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/admin")
def admin_page():
    return FileResponse(STATIC / "admin.html")
