import time
from app.sessions import SessionStore


def test_persists_across_restart(tmp_path):
    db = tmp_path / "s.db"
    SessionStore(db).append_turn("a", "hi", "hello")
    assert SessionStore(db).history("a") == [{"role": "user", "content": "hi"},
                                             {"role": "assistant", "content": "hello"}]


def test_keeps_last_six_turns_and_isolates_sessions():
    s = SessionStore(":memory:")
    for i in range(9):
        s.append_turn("a", f"q{i}", f"a{i}")
    s.append_turn("b", "other", "x")
    h = s.history("a")
    assert len(h) == 12 and h[0]["content"] == "q3" and h[-1]["content"] == "a8"
    assert len(s.history("b")) == 2


def test_purge_expired():
    s = SessionStore(":memory:", ttl_days=1)
    s.append_turn("old", "q", "a")
    s.db.execute("UPDATE messages SET ts=?", (time.time() - 3 * 86400,))
    s.append_turn("new", "q", "a")
    assert s.purge_expired() == 2
    assert s.history("old") == [] and len(s.history("new")) == 2
