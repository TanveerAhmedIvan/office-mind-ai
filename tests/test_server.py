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
    monkeypatch.setattr(server, "hybrid_search", lambda q, k, allowed=None, trace=None: CH)
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
    msgs = cl.get("/sessions/" + sid).json()["messages"]
    assert msgs[0]["content"] == "hi" and msgs[1]["trace_id"]
    tr = cl.get("/traces/%d" % msgs[1]["trace_id"]).json()
    assert tr["question"] == "hi" and tr["role"] == "user" and tr["ms"]["total"] >= 0 and tr["model"]
    assert "event: trace" in r.text


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
    monkeypatch.setattr(server, "hybrid_search", lambda q, k, allowed=None, trace=None: seen.setdefault("a", allowed) and CH or CH)
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


def test_session_list_full_history_and_delete(monkeypatch):
    cl, st = client(monkeypatch)
    login(cl)
    sid = None
    for i in range(8):  # more than 6 turns: all kept for display, model context still trimmed
        r = cl.post("/chat", json={"message": f"question {i}", "session_id": sid})
        sid = r.text.split('"session_id": "')[1].split('"')[0]
    lst = cl.get("/sessions").json()
    assert len(lst) == 1 and lst[0]["sid"] == sid and lst[0]["title"] == "question 0" and lst[0]["messages"] == 16
    assert len(cl.get("/sessions/" + sid).json()["messages"]) == 16 and len(st.history(sid)) == 12
    other = TestClient(server.app)
    server.auth.create_user("b@nodi.tech", "B", "password1", "user"); login(other, "b@nodi.tech", "password1")
    assert other.get("/sessions").json() == [] and other.delete("/sessions/" + sid).status_code == 403
    assert cl.delete("/sessions/" + sid).status_code == 200
    assert cl.get("/sessions").json() == [] and cl.get("/sessions/" + sid).json()["messages"] == []


def test_account_pages_served_and_password_flow(monkeypatch):
    cl, _ = client(monkeypatch)
    for path, marker in (("/password", "Change password"), ("/admin", "OfficeMind Admin"), ("/", "OfficeMind AI")):
        r = cl.get(path)
        assert r.status_code == 200 and marker in r.text
    js = cl.get("/assets/sidebar.js").text  # shared sidebar: account + admin links
    assert 'href="/admin#create-user"' in js and 'href="/password"' in js and "Sign out" in js and "+ New chat" in js
    assert 'id="create-role"' in cl.get("/admin").text and 'id="create-user"' in cl.get("/admin").text


def test_sidebar_assets_and_every_page_uses_them(monkeypatch):
    cl, _ = client(monkeypatch)
    assert "window.Sidebar" in cl.get("/assets/sidebar.js").text and ".side" in cl.get("/assets/sidebar.css").text
    for path in ("/", "/admin", "/password"):
        t = cl.get(path).text
        assert "/assets/sidebar.js" in t and 'id="side"' in t and "Sidebar.init" in t
    assert 'active:\'admin\'' in cl.get("/admin").text and 'active:\'password\'' in cl.get("/password").text
