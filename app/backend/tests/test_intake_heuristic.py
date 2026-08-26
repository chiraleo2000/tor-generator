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


ECT_CHATBOT_PACK = """
โครงการพัฒนาระบบตอบกลับอัตโนมัติคลังความรู้ปัญญาประดิษฐ์ (ECT AI Chatbot) ของสำนักงาน กกต. วงเงินงบประมาณ 15,000,000 บาท (ราคากลาง 15,075,250 บาท) ด้วยวิธี e-bidding กำหนดระยะเวลาดำเนินงาน 360 วัน โดยมีแนวทางการพัฒนาระบบและกฎระเบียบข้อบังคับตามขอบเขตงาน (TOR) ดังนี้
แนวทางการพัฒนาระบบและสถาปัตยกรรม (3 ระบบหลัก)
 - โครงสร้างพื้นฐาน: พัฒนาแบบ Containerized บน Kubernetes ติดตั้งบนบริการคลาวด์ในประเทศ
 - ระบบฐานข้อมูลความรู้ร่วม (Knowledge Base): รองรับข้อมูลเริ่มต้น 1.5 TB
 - ระบบ ECT AI Chatbot สำหรับบุคลากรภายใน: ใช้สถาปัตยกรรม RAG แบบ Strict Grounding
แผนการส่งมอบงานและการจ่ายเงิน (4 งวดงาน)
 - งวดที่ 1 (ภายใน 60 วัน, 15%): ส่งมอบแผนงานโครงการ
 - งวดที่ 2 (ภายใน 240 วัน, 35%): ติดตั้ง Cloud และ 3 ระบบหลัก
กฎระเบียบ มาตรฐาน และข้อบังคับสำคัญ
 - คุณสมบัติผู้ยื่นข้อเสนอและทีมงาน: เป็นนิติบุคคลไทยอายุ 3 ปี ทุนจดทะเบียนชำระแล้ว 3 ล้านบาท มีบุคลากรหลักครบ 8 ตำแหน่ง
 - เกณฑ์การคัดเลือก (Price Performance): สัดส่วนราคา 20% และข้อเสนอด้านเทคนิค 80%
 - ความมั่นคงปลอดภัยและ External LLM: ปฏิบัติตาม PDPA เข้ารหัส AES-256 และ TLS 1.3
 - กรรมสิทธิ์ SLA และ Exit Strategy: ข้อมูลเป็นกรรมสิทธิ์ของ กกต. ค่าปรับส่งมอบงานล่าช้า 0.10%/วัน
"""


def test_extract_unstructured_ect_chatbot_pack():
    found = extract_slot_contents(ECT_CHATBOT_PACK)
    assert found["s1"].startswith("โครงการพัฒนาระบบตอบกลับอัตโนมัติ")
    assert "15,000,000" in found["s6"]
    assert "360" in found["s5"]
    assert "กกต" in found["s7"]
    assert "Kubernetes" in found["s4.1"]
    assert "งวดที่ 1" in found["s8"]
    assert "นิติบุคคลไทย" in found["s3"]
    assert "Price Performance" in found["s11"] or "80%" in found["s11"]
    assert "PDPA" in found["s4.14"]
    assert "กรรมสิทธิ์" in found["s13"]
    assert "ค่าปรับ" in found["s10"]
    assert found.get("s4")
    assert "SLA" in found["s9"] or "กรรมสิทธิ์" in found["s9"]
    assert "Kubernetes" in found["s4.3"]


def test_extract_full_ect_ai_chatbot_fixture():
    from pathlib import Path

    text = Path(__file__).with_name("fixtures").joinpath("ect_ai_chatbot_pack.txt").read_text(
        encoding="utf-8"
    )
    found = extract_slot_contents(text)
    for key in ("s1", "s2", "s5", "s6", "s7", "s4.1", "s8", "s3", "s11", "s4.14", "s13", "s10"):
        assert found.get(key), f"expected {key} filled from ECT pack"


def test_short_mention_of_project_does_not_fake_background():
    found = extract_slot_contents("เนื้อหาโครงการยังไม่ติดรหัสช่อง")
    assert "s1" not in found
    assert "s6" not in found


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
