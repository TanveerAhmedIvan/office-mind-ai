"""T5/T6: users, roles, per-role document permissions, login tokens, session ownership (SQLite)."""
from __future__ import annotations
import hashlib, hmac, os, secrets, sqlite3, time
from . import config
from .ingest import DATA_DIR

TOKEN_TTL = 12 * 3600
DEFAULT_PASSWORD = "password"


def hash_pw(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    return salt.hex() + "$" + hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def verify_pw(pw: str, stored: str) -> bool:
    salt, h = stored.split("$")
    return hmac.compare_digest(hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex(), h)


def doc_names() -> list[str]:
    return sorted(p.name for p in DATA_DIR.iterdir() if p.suffix in (".md", ".pdf"))


class AuthStore:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        for ddl in (
            "CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, pw TEXT NOT NULL, "
            "role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)",
            "CREATE TABLE IF NOT EXISTS roles (name TEXT PRIMARY KEY, all_docs INTEGER NOT NULL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS role_docs (role TEXT, doc TEXT, PRIMARY KEY (role, doc))",
            "CREATE TABLE IF NOT EXISTS tokens (token TEXT PRIMARY KEY, email TEXT, exp REAL)",
            "CREATE TABLE IF NOT EXISTS session_owner (sid TEXT PRIMARY KEY, email TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, "
            "day TEXT NOT NULL, ts REAL NOT NULL, q_chars INTEGER NOT NULL, a_chars INTEGER NOT NULL DEFAULT 0)",
            "CREATE INDEX IF NOT EXISTS idx_usage ON usage(email, day)"):
            db.execute(ddl)
        if "daily_limit" not in [r[1] for r in db.execute("PRAGMA table_info(users)")]:
            db.execute("ALTER TABLE users ADD COLUMN daily_limit INTEGER")  # NULL = default limit
        db.commit()
        self.seed()

    def seed(self) -> None:
        if not self.db.execute("SELECT 1 FROM roles").fetchone():
            self.db.executemany("INSERT INTO roles(name, all_docs) VALUES (?, 1)", [("admin",), ("user",)])
        if not self.db.execute("SELECT 1 FROM users").fetchone():
            self.db.executemany("INSERT INTO users(email, name, pw, role) VALUES (?,?,?,?)",
                                [("admin@nodi.tech", "Admin", hash_pw(DEFAULT_PASSWORD), "admin"),
                                 ("ivan@nodi.tech", "Ivan", hash_pw(DEFAULT_PASSWORD), "user")])
        self.db.commit()

    # ---- login ----
    def login(self, email: str, password: str) -> str | None:
        row = self.db.execute("SELECT pw, active FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        ok = row is not None and verify_pw(password, row[0])
        if not ok or not row[1]:
            return None
        token = secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO tokens VALUES (?,?,?)", (token, email.strip().lower(), time.time() + TOKEN_TTL))
        self.db.commit()
        return token

    def user_for_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        self.db.execute("DELETE FROM tokens WHERE exp < ?", (time.time(),))
        row = self.db.execute("SELECT u.email, u.name, u.role FROM tokens t JOIN users u ON u.email=t.email "
                              "WHERE t.token=? AND u.active=1", (token,)).fetchone()
        return {"email": row[0], "name": row[1], "role": row[2]} if row else None

    def logout(self, token: str | None) -> None:
        self.db.execute("DELETE FROM tokens WHERE token=?", (token,)); self.db.commit()

    # ---- users ----
    def list_users(self) -> list[dict]:
        return [{"email": e, "name": n, "role": r, "active": bool(a)} for e, n, r, a in
                self.db.execute("SELECT email, name, role, active FROM users ORDER BY email")]

    def create_user(self, email: str, name: str, password: str, role: str, daily_limit: int | None = None) -> None:
        if not self.db.execute("SELECT 1 FROM roles WHERE name=?", (role,)).fetchone():
            raise ValueError("unknown role")
        try:
            self.db.execute("INSERT INTO users(email, name, pw, role, daily_limit) VALUES (?,?,?,?,?)",
                            (email.strip().lower(), name, hash_pw(password), role, daily_limit))
        except sqlite3.IntegrityError:
            raise ValueError("user exists")
        self.db.commit()

    def update_user(self, email: str, role=None, active=None, password=None, name=None, daily_limit=None) -> None:
        if role is not None and not self.db.execute("SELECT 1 FROM roles WHERE name=?", (role,)).fetchone():
            raise ValueError("unknown role")
        for col, val in (("role", role), ("active", None if active is None else int(active)),
                         ("pw", None if password is None else hash_pw(password)), ("name", name)):
            if val is not None:
                self.db.execute(f"UPDATE users SET {col}=? WHERE email=?", (val, email))
        if daily_limit is not None:  # -1 = back to the default limit
            self.db.execute("UPDATE users SET daily_limit=? WHERE email=?", (None if daily_limit < 0 else daily_limit, email))
        if active is False or password is not None:
            self.db.execute("DELETE FROM tokens WHERE email=?", (email,))
        self.db.commit()

    def delete_user(self, email: str) -> None:
        self.db.execute("DELETE FROM users WHERE email=?", (email,))
        self.db.execute("DELETE FROM tokens WHERE email=?", (email,)); self.db.commit()

    def admin_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]

    def check_password(self, email: str, password: str) -> bool:
        row = self.db.execute("SELECT pw FROM users WHERE email=?", (email,)).fetchone()
        return bool(row) and verify_pw(password, row[0])

    # ---- roles and document permissions ----
    def list_roles(self) -> list[dict]:
        return [{"name": n, "all_docs": bool(a), "docs": sorted(d for (d,) in self.db.execute(
            "SELECT doc FROM role_docs WHERE role=?", (n,)))}
            for n, a in self.db.execute("SELECT name, all_docs FROM roles ORDER BY name")]

    def set_role(self, name: str, all_docs: bool, docs: list[str]) -> None:
        if name == "admin":
            all_docs = True  # admin can never lose access
        valid = set(doc_names())
        self.db.execute("INSERT INTO roles(name, all_docs) VALUES (?,?) ON CONFLICT(name) DO UPDATE SET all_docs=excluded.all_docs",
                        (name, int(all_docs)))
        self.db.execute("DELETE FROM role_docs WHERE role=?", (name,))
        self.db.executemany("INSERT INTO role_docs VALUES (?,?)", [(name, d) for d in docs if d in valid])
        self.db.commit()

    def delete_role(self, name: str) -> None:
        if name == "admin" or self.db.execute("SELECT 1 FROM users WHERE role=?", (name,)).fetchone():
            raise ValueError("role is admin or still in use")
        self.db.execute("DELETE FROM roles WHERE name=?", (name,))
        self.db.execute("DELETE FROM role_docs WHERE role=?", (name,)); self.db.commit()

    def allowed_docs(self, role: str) -> set[str] | None:
        """None = every document; otherwise the set of file names this role may read."""
        row = self.db.execute("SELECT all_docs FROM roles WHERE name=?", (role,)).fetchone()
        if row and row[0]:
            return None
        return {d for (d,) in self.db.execute("SELECT doc FROM role_docs WHERE role=?", (role,))}

    # ---- usage and limits ----
    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d")

    def limit_for(self, email: str) -> int:
        """Messages per day for this user; 0 = unlimited."""
        row = self.db.execute("SELECT daily_limit FROM users WHERE email=?", (email,)).fetchone()
        return config.DEFAULT_DAILY_LIMIT if not row or row[0] is None else row[0]

    def used_today(self, email: str) -> int:
        return self.db.execute("SELECT COUNT(*) FROM usage WHERE email=? AND day=?", (email, self._today())).fetchone()[0]

    def start_usage(self, email: str, q_chars: int) -> int | None:
        """Counts one message against today's limit. Returns the usage row id, or None if over the limit."""
        limit = self.limit_for(email)
        if limit and self.used_today(email) >= limit:
            return None
        cur = self.db.execute("INSERT INTO usage(email, day, ts, q_chars) VALUES (?,?,?,?)",
                              (email, self._today(), time.time(), q_chars))
        self.db.commit()
        return cur.lastrowid

    def finish_usage(self, row_id: int, a_chars: int) -> None:
        self.db.execute("UPDATE usage SET a_chars=? WHERE id=?", (a_chars, row_id)); self.db.commit()

    def usage_report(self) -> list[dict]:
        """One row per user: today / last 7 days / all time, approx tokens (4 chars each), limit, last use."""
        week = time.strftime("%Y-%m-%d", time.localtime(time.time() - 6 * 86400))
        out = []
        for e, n, role, active in self.db.execute("SELECT email, name, role, active FROM users ORDER BY email"):
            def q(where, *a):
                return self.db.execute(f"SELECT COUNT(*), COALESCE(SUM(q_chars),0), COALESCE(SUM(a_chars),0), "
                                       f"MAX(ts) FROM usage WHERE email=? {where}", (e, *a)).fetchone()
            t, w, al = q("AND day=?", self._today()), q("AND day>=?", week), q("")
            out.append({"email": e, "name": n, "role": role, "active": bool(active),
                        "limit": self.limit_for(e), "today": t[0], "week": w[0], "total": al[0],
                        "tokens_in": al[1] // 4, "tokens_out": al[2] // 4,
                        "last_used": al[3] and time.strftime("%Y-%m-%d %H:%M", time.localtime(al[3]))})
        return out

    # ---- chat session ownership ----
    def claim_session(self, sid: str, email: str) -> bool:
        row = self.db.execute("SELECT email FROM session_owner WHERE sid=?", (sid,)).fetchone()
        if row:
            return row[0] == email
        self.db.execute("INSERT INTO session_owner VALUES (?,?)", (sid, email)); self.db.commit()
        return True

    def session_owner(self, sid: str) -> str | None:
        row = self.db.execute("SELECT email FROM session_owner WHERE sid=?", (sid,)).fetchone()
        return row[0] if row else None
