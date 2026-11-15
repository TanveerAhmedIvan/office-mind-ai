from fastapi.testclient import TestClient
from app import server
from app.sessions import SessionStore
from tests.test_chat import FakeLLM, CH


def test_chat_endpoint_streams_and_remembers(monkeypatch):
    monkeypatch.setattr(server, "llm", FakeLLM("ok [x.md]"))
    monkeypatch.setattr("app.chat.hybrid_search", lambda q, k: CH)
    import app.chat as c
    monkeypatch.setattr(c.answer, "__defaults__", (lambda q, k: CH,))
    monkeypatch.setattr(server, "store", SessionStore(":memory:"))
    cl = TestClient(server.app)
    r = cl.post("/chat", json={"message": "hi"})
    assert "event: meta" in r.text and "event: token" in r.text and "event: done" in r.text
    sid = r.text.split('"session_id": "')[1].split('"')[0]
    assert len(server.store.history(sid)) == 2


def test_session_endpoint_returns_history(monkeypatch):
    s = SessionStore(":memory:")
    s.append_turn("abc", "hi", "hello")
    monkeypatch.setattr(server, "store", s)
    r = TestClient(server.app).get("/sessions/abc")
    assert r.json()["messages"] == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    assert TestClient(server.app).get("/sessions/none").json()["messages"] == []


def test_feedback_endpoint(monkeypatch):
    s = SessionStore(":memory:")
    monkeypatch.setattr(server, "store", s)
    r = TestClient(server.app).post("/feedback", json={"session_id": "x", "rating": 1, "question": "q", "answer": "a"})
    assert r.json() == {"ok": True}
    assert s.db.execute("SELECT rating FROM feedback").fetchall() == [(1,)]
