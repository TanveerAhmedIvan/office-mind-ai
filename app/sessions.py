"""T1: SQLite-backed chat sessions. Survives restarts; keeps the last MAX_TURNS turns; expires old ones."""
from __future__ import annotations
import sqlite3, time
from pathlib import Path
from . import config


class SessionStore:
    def __init__(self, path: str | Path | None = None, ttl_days: float | None = None):
        self.path = str(path or config.SESSION_DB)
        self.ttl = (config.SESSION_TTL_DAYS if ttl_days is None else ttl_days) * 86400
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS messages ("
                        "id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT NOT NULL, "
                        "role TEXT NOT NULL, content TEXT NOT NULL, ts REAL NOT NULL)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_sid ON messages(sid, id)")
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback ("
                        "id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT, rating INTEGER NOT NULL, "
                        "question TEXT, answer TEXT, ts REAL NOT NULL)")
        self.db.commit()

    def history(self, sid: str, turns: int = config.MAX_TURNS) -> list[dict]:
        rows = self.db.execute("SELECT role, content FROM messages WHERE sid=? ORDER BY id DESC LIMIT ?",
                               (sid, 2 * turns)).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    def append_turn(self, sid: str, user: str, assistant: str) -> None:
        now = time.time()
        self.db.executemany("INSERT INTO messages(sid, role, content, ts) VALUES (?,?,?,?)",
                            [(sid, "user", user, now), (sid, "assistant", assistant, now)])
        self.db.execute("DELETE FROM messages WHERE sid=? AND id NOT IN "
                        "(SELECT id FROM messages WHERE sid=? ORDER BY id DESC LIMIT ?)",
                        (sid, sid, 2 * config.MAX_TURNS))
        self.db.commit()

    def add_feedback(self, sid: str | None, rating: int, question: str = "", answer: str = "") -> None:
        """Feedback is kept after the chat expires (it holds the Q/A it rates)."""
        self.db.execute("INSERT INTO feedback(sid, rating, question, answer, ts) VALUES (?,?,?,?,?)",
                        (sid, 1 if rating > 0 else -1, question, answer, time.time()))
        self.db.commit()

    def purge_expired(self) -> int:
        if self.ttl <= 0:
            return 0
        cur = self.db.execute("DELETE FROM messages WHERE sid IN "
                              "(SELECT sid FROM messages GROUP BY sid HAVING MAX(ts) < ?)",
                              (time.time() - self.ttl,))
        self.db.commit()
        return cur.rowcount
