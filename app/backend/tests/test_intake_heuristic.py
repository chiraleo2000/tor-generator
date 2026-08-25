"""Unit tests for labelled-paste slot extraction."""

from app.services.intake_heuristic import extract_slot_contents, overlay_filled_slots


def test_extract_slot_contents_reads_codes():
    text = (
        "ความเป็นมา (s1): กรมบัญชีกลางจัดซื้อระบบ\n"
        "วัตถุประสงค์ (s2): เพื่อบริหารสัญญา\n"
        "ระยะเวลาดำเนินการ (s5): 180 วัน\n"
        "วงเงินงบประมาณ (s6): 2500000 บาท"
    )
    found = extract_slot_contents(text)
    assert "กรมบัญชีกลาง" in found["s1"]
    assert "บริหารสัญญา" in found["s2"]
    assert "180" in found["s5"]
    assert "2500000" in found["s6"]


def test_overlay_filled_slots_does_not_clobber_facts():
    base = {
        "s1": {"content": "จากเอกสาร", "status": "filled", "sources": ["paste"]},
        "s10": {"content": "", "status": "gap", "sources": []},
    }
    incoming = {
        "s1": {"content": "จากโมเดล", "status": "filled", "sources": ["llm"]},
        "s10": {"content": "พ.ร.บ.", "status": "reference_only", "sources": ["rag"]},
    }
    merged = overlay_filled_slots(base, incoming)
    assert merged["s1"]["content"] == "จากโมเดล"
    assert merged["s10"]["status"] == "reference_only"
