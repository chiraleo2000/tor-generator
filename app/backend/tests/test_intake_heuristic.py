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


def test_overlay_filled_slots_keeps_paste_facts():
    base = {
        "s1": {"content": "จากเอกสาร", "status": "filled", "sources": ["paste"]},
        "s10": {"content": "", "status": "gap", "sources": []},
    }
    incoming = {
        "s1": {"content": "จากโมเดล", "status": "filled", "sources": ["llm"]},
        "s10": {"content": "พ.ร.บ.", "status": "reference_only", "sources": ["rag"]},
    }
    merged = overlay_filled_slots(base, incoming)
    assert merged["s1"]["content"] == "จากเอกสาร"
    assert merged["s10"]["status"] == "reference_only"


def test_repair_moves_qualifications_out_of_duration():
    from app.services.intake_heuristic import repair_misplaced_slots

    slots = {
        "s3": {"content": "", "status": "gap", "sources": []},
        "s5": {
            "content": "นิติบุคคลไทยจัดตั้งมาแล้วไม่น้อยกว่า 3 ปี ทุนจดทะเบียนชำระเต็ม",
            "status": "filled",
            "sources": ["llm"],
        },
    }
    fixed = repair_misplaced_slots(slots)
    assert fixed["s5"]["status"] == "gap"
    assert "นิติบุคคล" in fixed["s3"]["content"]
    assert fixed["s3"]["status"] == "filled"
