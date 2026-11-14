import pytest
from app.ingest import DATA_DIR, chunk_markdown

MD = sorted(DATA_DIR.glob("*.md"))


def test_all_files_present():
    assert len(MD) == 11 and len(list(DATA_DIR.glob("*.pdf"))) == 1


def test_leave_table_kept_intact():
    ch = chunk_markdown(DATA_DIR / "employee_handbook_v3.md")
    leave = [c for c in ch if "Annual leave | 18" in c.text]
    assert leave and "Paternity leave" in leave[0].text


def test_error_code_chunk():
    ch = chunk_markdown(DATA_DIR / "nodidesk_error_codes.md")
    assert any("ND-1042" in c.text and "Rate limit" in c.text for c in ch)


def test_superseded_flag_and_bangla():
    old = chunk_markdown(DATA_DIR / "leave_policy_v2.1_2024_SUPERSEDED.md")
    assert old and all(c.superseded for c in old)
    bn = chunk_markdown(DATA_DIR / "office_transport_canteen_bn.md")
    assert all(c.lang == "bn" for c in bn) and "ক্যান্টিন" in "".join(c.text for c in bn)


def test_pdf_tables():
    pytest.importorskip("pdfplumber")
    from app.ingest import chunk_pdf
    ch = chunk_pdf(next(DATA_DIR.glob("*.pdf")))
    assert any("|" in c.text for c in ch)
