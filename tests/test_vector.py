import pytest
pytest.importorskip("qdrant_client")
from app import config, vector
from app.ingest import ingest_all


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    c = vector.QdrantClient(path=str(tmp_path_factory.mktemp("q")))
    vector.build_index(ingest_all(), c)
    return c


def top_sources(q, client):
    return [r["source"] for r in vector.search(q, 5, client)]


def test_leave_question(client):
    assert "employee_handbook_v3.md" in top_sources("How many days of annual leave do I get?", client)


def test_expense_pdf(client):
    assert "expense_reimbursement_policy.pdf" in top_sources("What is the hotel limit outside Dhaka?", client)


def test_bangla_doc_english_question(client):
    assert "office_transport_canteen_bn.md" in top_sources("What time does the Uttara bus leave?", client)
