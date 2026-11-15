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
