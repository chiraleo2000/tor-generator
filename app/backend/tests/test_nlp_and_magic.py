"""Unit tests for magic-byte upload detection and Phase 0 NLP fields."""

from app.domain.extraction_map import extract_nlp_fields, mapping_rows
from app.domain.file_magic import detect_mime, require_allowed_upload


def test_detect_pdf_magic():
    assert detect_mime(b"%PDF-1.4 rest of file") == "application/pdf"


def test_reject_executable():
    try:
        require_allowed_upload(b"MZ\x90\x00not-a-document", "application/octet-stream")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_reject_pdf_claim_without_magic():
    try:
        require_allowed_upload(b"not a pdf file at all", "application/pdf")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_detect_png_magic():
    assert detect_mime(b"\x89PNG\r\n\x1a\nXXXX") == "image/png"


def test_mapping_rows_partial_when_empty():
    rows = mapping_rows({})
    assert rows[0]["tag"] == "partial"


def test_nlp_extracts_budget_and_ministry():
    text = (
        "โครงการจ้างพัฒนาระบบ e-Payment กรมสรรพากร "
        "วงเงินงบประมาณ 5,000,000 บาท ระยะเวลาดำเนินการ 180 วัน "
        "ปัญหาที่พบคือระบบเดิมล้าสมัย เกณฑ์ราคา (Price) งวด 30% 40% 30%"
    )
    fields = extract_nlp_fields(text)
    assert fields["ministry"] == "กรมสรรพากร"
    assert fields["budget"] == 5000000
    assert "paidupSuggest" in fields
    rows = mapping_rows(fields)
    assert any(row["tag"] == "matched" for row in rows)
