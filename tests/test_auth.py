import sqlite3, time
from app.auth import AuthStore, verify_pw, hash_pw


def mk():
    return AuthStore(sqlite3.connect(":memory:", check_same_thread=False))


def test_seed_users_and_default_password():
    a = mk()
    assert {u["email"]: u["role"] for u in a.list_users()} == {"admin@nodi.tech": "admin", "ivan@nodi.tech": "user"}
    assert a.login("ivan@nodi.tech", "password") and a.login("Admin@Nodi.tech", "password")
    assert a.login("ivan@nodi.tech", "wrong") is None and a.login("nobody@x.y", "password") is None
    assert verify_pw("x", hash_pw("x")) and not verify_pw("y", hash_pw("x"))


def test_token_lookup_logout_expiry_disable():
    a = mk()
    t = a.login("ivan@nodi.tech", "password")
    assert a.user_for_token(t)["role"] == "user"
    a.logout(t); assert a.user_for_token(t) is None
    t = a.login("ivan@nodi.tech", "password")
    a.db.execute("UPDATE tokens SET exp=?", (time.time() - 1,)); assert a.user_for_token(t) is None
    t = a.login("ivan@nodi.tech", "password"); a.update_user("ivan@nodi.tech", active=False)
    assert a.user_for_token(t) is None and a.login("ivan@nodi.tech", "password") is None


def test_roles_and_doc_permissions():
    a = mk()
    assert a.allowed_docs("user") is None and a.allowed_docs("admin") is None  # seeded: all docs
    a.set_role("hr", False, ["employee_handbook_v3.md", "not_a_file.md"])
    assert a.allowed_docs("hr") == {"employee_handbook_v3.md"}
    a.set_role("admin", False, [])
    assert a.allowed_docs("admin") is None  # admin can never lose access
    a.create_user("h@nodi.tech", "H", "password1", "hr")
    try:
        a.delete_role("hr"); assert False
    except ValueError:
        pass
    try:
        a.create_user("z@nodi.tech", "Z", "password1", "ghost"); assert False
    except ValueError:
        pass


def test_session_ownership():
    a = mk()
    assert a.claim_session("s1", "a@x") and a.claim_session("s1", "a@x") and not a.claim_session("s1", "b@x")


def test_bm25_respects_allowed_docs():
    from app.hybrid import bm25_search
    hits = bm25_search("annual leave days", 20, allowed={"nodidesk_faq.md"})
    assert all(c.source == "nodidesk_faq.md" for c, _ in hits)
    assert bm25_search("annual leave days", 20, allowed={"employee_handbook_v3.md"})


def test_limits_and_usage_report():
    a = mk()
    assert a.limit_for("ivan@nodi.tech") == 50  # default
    a.update_user("ivan@nodi.tech", daily_limit=2)
    r1, r2 = a.start_usage("ivan@nodi.tech", 40), a.start_usage("ivan@nodi.tech", 80)
    assert r1 and r2 and a.start_usage("ivan@nodi.tech", 4) is None  # 3rd blocked
    a.finish_usage(r1, 400)
    a.update_user("ivan@nodi.tech", daily_limit=0)  # unlimited
    assert a.start_usage("ivan@nodi.tech", 4)
    a.update_user("ivan@nodi.tech", daily_limit=-1)
    assert a.limit_for("ivan@nodi.tech") == 50
    row = next(x for x in a.usage_report() if x["email"] == "ivan@nodi.tech")
    assert (row["today"], row["week"], row["total"], row["tokens_in"], row["tokens_out"]) == (3, 3, 3, 31, 100)
    assert next(x for x in a.usage_report() if x["email"] == "admin@nodi.tech")["total"] == 0
