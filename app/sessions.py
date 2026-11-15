"""T1: SQLite-backed chat sessions. Survives restarts; keeps the last MAX_TURNS turns; expires old ones."""
from __future__ import annotations
import json, sqlite3, time
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
        self.db.execute("CREATE TABLE IF NOT EXISTS traces (msg_id INTEGER PRIMARY KEY, sid TEXT NOT NULL, "
                        "data TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback ("
                        "id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT, rating INTEGER NOT NULL, "
                        "question TEXT, answer TEXT, ts REAL NOT NULL)")
        self.db.commit()

    def history(self, sid: str, turns: int = config.MAX_TURNS) -> list[dict]:
        rows = self.db.execute("SELECT role, content FROM messages WHERE sid=? ORDER BY id DESC LIMIT ?",
                               (sid, 2 * turns)).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    def history_with_trace(self, sid: str, turns: int = config.MAX_TURNS) -> list[dict]:
        rows = self.db.execute(
            "SELECT m.id, m.role, m.content, t.msg_id IS NOT NULL FROM messages m LEFT JOIN traces t ON t.msg_id=m.id "
            "WHERE m.sid=? ORDER BY m.id DESC LIMIT ?", (sid, 2 * turns)).fetchall()
        return [{"role": r, "content": c, "trace_id": i if has else None} for i, r, c, has in reversed(rows)]

    def save_trace(self, sid: str, msg_id: int, trace: dict) -> None:
        self.db.execute("INSERT OR REPLACE INTO traces VALUES (?,?,?)", (msg_id, sid, json.dumps(trace, ensure_ascii=False)))
        self.db.commit()

    def get_trace(self, msg_id: int) -> tuple[str, dict] | None:
        row = self.db.execute("SELECT sid, data FROM traces WHERE msg_id=?", (msg_id,)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def append_turn(self, sid: str, user: str, assistant: str) -> int:
        """Returns the id of the assistant message (used to attach its trace)."""
        now = time.time()
        self.db.execute("INSERT INTO messages(sid, role, content, ts) VALUES (?,?,?,?)", (sid, "user", user, now))
        msg_id = self.db.execute("INSERT INTO messages(sid, role, content, ts) VALUES (?,?,?,?)",
                                 (sid, "assistant", assistant, now)).lastrowid
        self.db.execute("DELETE FROM messages WHERE sid=? AND id NOT IN "
                        "(SELECT id FROM messages WHERE sid=? ORDER BY id DESC LIMIT ?)",
                        (sid, sid, 2 * config.MAX_TURNS))
        self.db.execute("DELETE FROM traces WHERE sid=? AND msg_id NOT IN (SELECT id FROM messages WHERE sid=?)", (sid, sid))
        self.db.commit()
        return msg_id

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
        self.db.execute("DELETE FROM traces WHERE msg_id NOT IN (SELECT id FROM messages)")
        self.db.commit()
        return cur.rowcount
