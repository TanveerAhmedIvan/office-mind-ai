import pytest
pytest.importorskip("rank_bm25")
from app.hybrid import tokenize, bm25_search, rrf


def test_tokenize_keeps_codes():
    t = tokenize("Error ND-1042 occurs")
    assert "nd-1042" in t and "1042" in t


def test_bm25_finds_exact_code():
    assert "nodidesk_error_codes.md" in [c.source for c, _ in bm25_search("ND-1042")[:3]]
    assert bm25_search("SEC-EXC")[0][0].source == "it_security_policy.md"


def test_bm25_bangla():
    assert bm25_search("ক্যান্টিন")[0][0].source == "office_transport_canteen_bn.md"


def test_rrf_prefers_agreement():
    s = rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert s["a"] > s["c"] and s["b"] > s["d"]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from app import vector
    from app.ingest import ingest_all
    c = vector.QdrantClient(path=str(tmp_path_factory.mktemp("q")))
    vector.build_index(ingest_all(), c)
    return c


def test_nd1042_finds_error_codes_first(client):
    from app.hybrid import hybrid_search
    assert hybrid_search("What does ND-1042 mean?", 5, client=client)[0]["source"] == "nodidesk_error_codes.md"


def test_current_handbook_beats_superseded(client):
    from app.hybrid import hybrid_search
    top = hybrid_search("How many days of annual leave do I get?", 5, client=client)[0]
    assert top["source"] == "employee_handbook_v3.md" and not top["superseded"]


def test_bangla_return_bus(client):
    from app.hybrid import hybrid_search
    assert "office_transport_canteen_bn.md" in [r["source"] for r in hybrid_search(
        "What time does the return office bus leave?", 5, client=client)]
