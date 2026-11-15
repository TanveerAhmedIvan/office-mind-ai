from fastapi.testclient import TestClient
from app import server
from app.sessions import SessionStore
from tests.test_chat import FakeLLM, CH


import sqlite3
from app.auth import AuthStore


def client(monkeypatch, llm=None):
    st = SessionStore(":memory:")
    monkeypatch.setattr(server, "store", st)
    monkeypatch.setattr(server, "auth", AuthStore(st.db))
    monkeypatch.setattr(server, "llm", llm or FakeLLM("ok [x.md]"))
    monkeypatch.setattr(server, "hybrid_search", lambda q, k, allowed=None: CH)
    return TestClient(server.app), st


def login(cl, email="ivan@nodi.tech", pw="password"):
    return cl.post("/login", json={"email": email, "password": pw})


def test_chat_requires_login_then_streams_and_remembers(monkeypatch):
    cl, st = client(monkeypatch)
    assert cl.post("/chat", json={"message": "hi"}).status_code == 401
    assert login(cl, pw="bad").status_code == 401
    assert login(cl).status_code == 200
    r = cl.post("/chat", json={"message": "hi"})
    assert "event: meta" in r.text and "event: token" in r.text and "event: done" in r.text
    sid = r.text.split('"session_id": "')[1].split('"')[0]
    assert len(st.history(sid)) == 2
    assert cl.get("/sessions/" + sid).json()["messages"][0]["content"] == "hi"


def test_other_user_cannot_read_or_use_chat(monkeypatch):
    cl, st = client(monkeypatch)
    login(cl)
    sid = cl.post("/chat", json={"message": "hi"}).text.split('"session_id": "')[1].split('"')[0]
    cl2 = TestClient(server.app)
    server.auth.create_user("b@nodi.tech", "B", "password1", "user")
    login(cl2, "b@nodi.tech", "password1")
    assert cl2.get("/sessions/" + sid).status_code == 403
    assert cl2.post("/chat", json={"message": "x", "session_id": sid}).status_code == 403
    cl3 = TestClient(server.app); login(cl3, "admin@nodi.tech")
    assert cl3.get("/sessions/" + sid).status_code == 200  # admin may read


def test_permissions_passed_to_search(monkeypatch):
    cl, st = client(monkeypatch)
    seen = {}
    monkeypatch.setattr(server, "hybrid_search", lambda q, k, allowed=None: seen.setdefault("a", allowed) and CH or CH)
    server.auth.set_role("hr", False, ["employee_handbook_v3.md"])
    server.auth.create_user("h@nodi.tech", "H", "password1", "hr")
    login(cl, "h@nodi.tech", "password1")
    cl.post("/chat", json={"message": "hi"})
    assert seen["a"] == {"employee_handbook_v3.md"}


def test_admin_api_and_user_forbidden(monkeypatch):
    cl, _ = client(monkeypatch)
    login(cl)
    assert cl.get("/admin/users").status_code == 403
    admin = TestClient(server.app); login(admin, "admin@nodi.tech")
    assert admin.put("/admin/roles/hr", json={"all_docs": False, "docs": ["it_security_policy.md"]}).status_code == 200
    assert admin.post("/admin/users", json={"email": "n@nodi.tech", "password": "password1", "role": "hr"}).status_code == 200
    assert admin.post("/admin/users", json={"email": "m@nodi.tech", "password": "short", "role": "hr"}).status_code == 400
    assert admin.delete("/admin/users/admin@nodi.tech").status_code == 400  # last admin / self
    assert admin.patch("/admin/users/admin@nodi.tech", json={"role": "user"}).status_code == 400
    assert any(r["name"] == "hr" and r["docs"] == ["it_security_policy.md"] for r in admin.get("/admin/roles").json())


def test_feedback_and_password_change(monkeypatch):
    cl, st = client(monkeypatch)
    assert cl.post("/feedback", json={"rating": 1}).status_code == 401
    login(cl)
    assert cl.post("/feedback", json={"session_id": "x", "rating": 1, "question": "q", "answer": "a"}).json() == {"ok": True}
    assert st.db.execute("SELECT rating FROM feedback").fetchall() == [(1,)]
    assert cl.post("/me/password", json={"old_password": "nope", "new_password": "longenough"}).status_code == 403
    assert cl.post("/me/password", json={"old_password": "password", "new_password": "longenough"}).status_code == 200
    assert login(cl).status_code == 401 and login(cl, pw="longenough").status_code == 200


def test_daily_limit_returns_429_and_admin_sees_usage(monkeypatch):
    cl, _ = client(monkeypatch)
    login(cl)
    admin = TestClient(server.app); login(admin, "admin@nodi.tech")
    assert admin.patch("/admin/users/ivan@nodi.tech", json={"daily_limit": 1}).status_code == 200
    assert cl.post("/chat", json={"message": "one"}).status_code == 200
    r = cl.post("/chat", json={"message": "two"})
    assert r.status_code == 429 and "daily limit" in r.json()["detail"]
    assert cl.get("/me").json()["used_today"] == 1 and cl.get("/me").json()["limit"] == 1
    row = next(x for x in admin.get("/admin/usage").json() if x["email"] == "ivan@nodi.tech")
    assert row["today"] == 1 and row["limit"] == 1 and row["tokens_out"] > 0
    assert cl.get("/admin/usage").status_code == 403
